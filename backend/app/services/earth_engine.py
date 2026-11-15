import os
import json
import logging
import math
import time
import uuid
from datetime import datetime, timezone, date
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import requests

try:
    import ee
    EE_AVAILABLE = True
except ImportError:
    ee = None
    EE_AVAILABLE = False

from app.config import (
    EE_PROJECT,
    EE_SERVICE_ACCOUNT_EMAIL,
    EE_PRIVATE_KEY_PATH,
    CACHE_TTL_HOURS
)
from app.utils.converters import json_safe

logger = logging.getLogger("prithvix.ee")

DEFAULT_START_DATE = "2026-01-01"
MAX_ANALYSIS_MONTHS = 120

SUPPORTED_DATASETS = (
    "smap", "gpm", "modis", "landsat", "nasa_power",
    "srtm", "grace", "ecostress"
)

DATASET_CATALOG = {
    "smap": {
        "name": "NASA SMAP L4 soil moisture",
        "earth_engine_id": "NASA/SMAP/SPL4SMGP/008",
        "nominal_scale_m": 11000,
        "temporal_resolution": "3-hourly; aggregated to calendar-month mean",
        "units": {"sm_surface": "m3/m3", "sm_rootzone": "m3/m3"},
        "caveat": (
            "Approximately 9 km model-assimilation product. A small field may "
            "fall within one or a few pixels; it is not field-scale soil sampling."
        ),
    },
    "gpm": {
        "name": "NASA GPM IMERG V07",
        "earth_engine_id": "NASA/GPM_L3/IMERG_V07",
        "nominal_scale_m": 11132,
        "temporal_resolution": "30-minute; aggregated to monthly rainfall",
        "units": {"rainfall_mm": "mm/month"},
        "caveat": (
            "Approximately 0.1 degree / 11.1 km. Monthly rainfall is calculated "
            "by multiplying each 30-minute precipitation rate (mm/hr) by 0.5 "
            "hour, summing per pixel, then averaging across the AOI."
        ),
    },
    "modis": {
        "name": "Terra MODIS vegetation indices",
        "earth_engine_id": "MODIS/061/MOD13Q1",
        "nominal_scale_m": 250,
        "temporal_resolution": "16-day; aggregated to calendar-month mean",
        "units": {"NDVI": "unitless", "EVI": "unitless"},
        "caveat": (
            "250 m vegetation-index product. Monthly values average available "
            "16-day composites after DetailedQA screening."
        ),
    },
    "landsat": {
        "name": "USGS Landsat 8 + 9 Collection 2 Tier 1 Level 2",
        "earth_engine_id": "LANDSAT/LC08/C02/T1_L2 + LANDSAT/LC09/C02/T1_L2",
        "nominal_scale_m": 30,
        "temporal_resolution": "Scene-based; aggregated to calendar-month mean",
        "units": {"NDVI": "unitless", "NDMI": "unitless", "LST_C": "deg C"},
        "caveat": (
            "30 m optical/thermal data. Clear-sky masking may leave months with "
            "few or no valid pixels. Surface-temperature pixels can be missing "
            "even when optical reflectance is available."
        ),
    },
    "nasa_power": {
        "name": "NASA POWER Daily Agroclimatology API",
        "earth_engine_id": None,
        "nominal_scale_m": None,
        "temporal_resolution": "Daily point data; aggregated to calendar-month",
        "units": {
            "PRECTOTCORR_monthly_sum": "mm/month",
            "T2M_monthly_mean": "deg C",
            "RH2M_monthly_mean": "%",
            "ALLSKY_SFC_SW_DWN_monthly_mean": "MJ/m2/day",
        },
        "caveat": (
            "POWER is sampled at the AOI centroid, not averaged over the full "
            "polygon. It is a gridded meteorological estimate, not a farm sensor."
        ),
    },
    "srtm": {
        "name": "NASA/USGS SRTM elevation",
        "earth_engine_id": "USGS/SRTMGL1_003",
        "nominal_scale_m": 30,
        "temporal_resolution": "Static elevation snapshot",
        "units": {
            "elevation_m_mean": "m",
            "elevation_m_min": "m",
            "elevation_m_max": "m",
            "slope_deg_mean": "degrees",
            "slope_deg_min": "degrees",
            "slope_deg_max": "degrees",
        },
        "caveat": (
            "Near-global SRTM coverage, not a complete polar/global DEM. "
            "Regional statistics are summarized at 90 m to limit computation."
        ),
    },
    "grace": {
        "name": "NASA GRACE / GRACE-FO JPL Mascon CRI",
        "earth_engine_id": "NASA/GRACE/MASS_GRIDS_V04/MASCON_CRI",
        "nominal_scale_m": 55660,
        "temporal_resolution": "Monthly",
        "units": {"lwe_thickness": "cm equivalent water thickness anomaly"},
        "caveat": (
            "Very coarse (~3-degree mascon) regional water-storage anomaly, "
            "not suitable for individual farms. The Earth Engine V04 CRI "
            "collection currently ends in September 2024."
        ),
    },
    "ecostress": {
        "name": "NASA ECOSTRESS L2T LSTE V2",
        "earth_engine_id": "NASA/ECOSTRESS/L2T_LSTE/V2",
        "nominal_scale_m": 70,
        "temporal_resolution": "Irregular observations; summarized by month",
        "units": {"LST_C": "deg C"},
        "caveat": (
            "Important coverage limitation: the Earth Engine catalog currently "
            "says only tiles covering the Los Angeles metro area have been "
            "ingested. Most AOIs will correctly return no_data."
        ),
    },
}

_EE_READY = False
_EE_AUTH_ERROR = None
_EE_CHECKED = False


def get_earth_engine_status() -> Dict[str, Any]:
    """Return status of Earth Engine connection and credentials."""
    return {
        "available": EE_AVAILABLE,
        "initialized": _EE_READY,
        "project": EE_PROJECT,
        "error": str(_EE_AUTH_ERROR) if _EE_AUTH_ERROR else None,
        "service_account_configured": bool(EE_SERVICE_ACCOUNT_EMAIL and EE_PRIVATE_KEY_PATH),
        "instructions": (
            "To authenticate Earth Engine locally, run 'earthengine authenticate' in terminal. "
            "For automated server deployments, set EE_SERVICE_ACCOUNT_EMAIL and EE_PRIVATE_KEY_PATH."
        ) if not _EE_READY else "Earth Engine is connected and ready."
    }


def initialize_earth_engine(project_id: Optional[str] = None, force_recheck: bool = False) -> bool:
    """Attempt non-interactive Earth Engine initialization."""
    global _EE_READY, _EE_AUTH_ERROR, _EE_CHECKED
    if _EE_CHECKED and not force_recheck:
        return _EE_READY
    _EE_CHECKED = True

    if not EE_AVAILABLE:
        _EE_AUTH_ERROR = "earthengine-api Python package is not installed."
        return False

    project = project_id or EE_PROJECT
    try:
        if EE_SERVICE_ACCOUNT_EMAIL and EE_PRIVATE_KEY_PATH and os.path.exists(EE_PRIVATE_KEY_PATH):
            credentials = ee.ServiceAccountCredentials(EE_SERVICE_ACCOUNT_EMAIL, EE_PRIVATE_KEY_PATH)
            ee.Initialize(credentials, project=project)
        else:
            ee.Initialize(project=project)
        _EE_READY = True
        _EE_AUTH_ERROR = None
        logger.info("Earth Engine successfully initialized with project: %s", project)
        return True
    except Exception as exc:
        _EE_READY = False
        _EE_AUTH_ERROR = exc
        logger.warning("Earth Engine initialization check: not authenticated (%s)", exc)
        return False


def _dataset_result(name: str, status: str, records=None, message=None, metadata=None) -> dict:
    catalog_entry = DATASET_CATALOG.get(name, {})
    result = {
        "status": status,
        "source": catalog_entry.get("name", name),
        "source_id": catalog_entry.get("earth_engine_id"),
        "nominal_scale_m": catalog_entry.get("nominal_scale_m"),
        "temporal_resolution": catalog_entry.get("temporal_resolution"),
        "units": catalog_entry.get("units", {}),
        "caveat": catalog_entry.get("caveat", ""),
        "records": records or [],
        "message": message,
    }
    if metadata:
        result["metadata"] = metadata
    return result


def _month_windows(start_date: str, end_date: str) -> List[dict]:
    start_ts = pd.Timestamp(start_date)
    end_ts = pd.Timestamp(end_date)
    cursor = start_ts.to_period("M").to_timestamp()
    windows = []
    while cursor < end_ts:
        next_month = cursor + pd.offsets.MonthBegin(1)
        window_start = max(cursor, start_ts)
        window_end = min(next_month, end_ts)
        windows.append({
            "period": cursor.strftime("%Y-%m"),
            "start": window_start.strftime("%Y-%m-%d"),
            "end": window_end.strftime("%Y-%m-%d"),
        })
        cursor = next_month
    return windows


def _monthly_reduce(
    collection,
    geometry,
    start_date: str,
    end_date: str,
    scale_m: int,
    output_bands: List[str],
    composite_method: str = "mean",
    image_mapper=None,
) -> List[dict]:
    features = []
    for window in _month_windows(start_date, end_date):
        month_collection = collection.filterBounds(geometry).filterDate(
            window["start"], window["end"]
        )
        if image_mapper is not None:
            month_collection = month_collection.map(image_mapper)

        if composite_method == "sum":
            composite = month_collection.sum()
        elif composite_method == "median":
            composite = month_collection.median()
        else:
            composite = month_collection.mean()

        image_count = month_collection.size()
        stats = ee.Dictionary(ee.Algorithms.If(
            image_count.gt(0),
            composite.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=geometry,
                scale=scale_m,
                maxPixels=1e13,
                bestEffort=True,
                tileScale=4,
            ),
            ee.Dictionary({})
        ))

        properties = ee.Dictionary({
            "period": window["period"],
            "image_count": image_count,
        }).combine(stats, True)
        features.append(ee.Feature(None, properties))

    if not features:
        return []
    info = ee.FeatureCollection(features).getInfo()
    return [f.get("properties", {}) for f in info.get("features", [])]


# --- Dataset Extractors ---

def extract_smap(geometry, start_date: str, end_date: str) -> dict:
    name = "smap"
    if not _EE_READY:
        return _dataset_result(name, "auth_required", message=f"Earth Engine authentication required: {_EE_AUTH_ERROR}")
    collection = (
        ee.ImageCollection(DATASET_CATALOG[name]["earth_engine_id"])
        .filterBounds(geometry)
        .filterDate(start_date, end_date)
        .select(["sm_surface", "sm_rootzone"])
    )
    total = int(collection.size().getInfo())
    if total == 0:
        return _dataset_result(name, "no_data", message="No SMAP images intersect this AOI/date range.")
    rows = _monthly_reduce(collection, geometry, start_date, end_date, 11000, ["sm_surface", "sm_rootzone"], "mean")
    has_values = any(r.get("sm_surface") is not None or r.get("sm_rootzone") is not None for r in rows)
    return _dataset_result(
        name, "ok" if has_values else "no_data",
        records=rows,
        message=None if has_values else "No monthly SMAP observations found for AOI.",
        metadata={"image_count_in_period": total, "reduction_scale_m": 11000}
    )


def _gpm_half_hour_to_mm(image):
    return (
        image.select("precipitation")
        .multiply(0.5)
        .rename("rainfall_mm")
        .copyProperties(image, image.propertyNames())
    )


def extract_gpm(geometry, start_date: str, end_date: str) -> dict:
    name = "gpm"
    if not _EE_READY:
        return _dataset_result(name, "auth_required", message=f"Earth Engine authentication required: {_EE_AUTH_ERROR}")
    collection = (
        ee.ImageCollection(DATASET_CATALOG[name]["earth_engine_id"])
        .filterBounds(geometry)
        .filterDate(start_date, end_date)
        .select("precipitation")
    )
    total = int(collection.size().getInfo())
    if total == 0:
        return _dataset_result(name, "no_data", message="No GPM IMERG images intersect this AOI/date range.")
    rows = _monthly_reduce(
        collection, geometry, start_date, end_date, 11132,
        ["rainfall_mm"], "sum", image_mapper=_gpm_half_hour_to_mm
    )
    has_values = any(r.get("rainfall_mm") is not None for r in rows)
    return _dataset_result(
        name, "ok" if has_values else "no_data",
        records=rows,
        metadata={
            "image_count_in_period": total,
            "reduction_scale_m": 11132,
            "calculation": "sum(precipitation_mm_per_hour * 0.5 hour), then AOI mean",
        }
    )


def _mask_and_scale_modis(image):
    qa = image.select("DetailedQA")
    good_quality = qa.bitwiseAnd(3).lte(1)
    scaled = image.select(["NDVI", "EVI"]).multiply(0.0001)
    return scaled.updateMask(good_quality).copyProperties(image, image.propertyNames())


def extract_modis(geometry, start_date: str, end_date: str) -> dict:
    name = "modis"
    if not _EE_READY:
        return _dataset_result(name, "auth_required", message=f"Earth Engine authentication required: {_EE_AUTH_ERROR}")
    collection = (
        ee.ImageCollection(DATASET_CATALOG[name]["earth_engine_id"])
        .filterBounds(geometry)
        .filterDate(start_date, end_date)
    )
    total = int(collection.size().getInfo())
    if total == 0:
        return _dataset_result(name, "no_data", message="No MODIS vegetation-index images intersect this AOI/date range.")
    rows = _monthly_reduce(collection, geometry, start_date, end_date, 250, ["NDVI", "EVI"], "mean", image_mapper=_mask_and_scale_modis)
    has_values = any(r.get("NDVI") is not None or r.get("EVI") is not None for r in rows)
    return _dataset_result(
        name, "ok" if has_values else "no_data",
        records=rows,
        metadata={"image_count_in_period": total, "reduction_scale_m": 250, "qa_rule": "DetailedQA bits 0-1 <= 1"}
    )


def _prepare_landsat(image):
    qa = image.select("QA_PIXEL")
    mask = qa.bitwiseAnd(1 << 0).eq(0)
    for bit in (1, 2, 3, 4, 5):
        mask = mask.And(qa.bitwiseAnd(1 << bit).eq(0))
    mask = mask.And(image.select("QA_RADSAT").eq(0))

    sr = image.select(["SR_B4", "SR_B5", "SR_B6"]).multiply(0.0000275).add(-0.2)
    ndvi = sr.normalizedDifference(["SR_B5", "SR_B4"]).rename("NDVI")
    ndmi = sr.normalizedDifference(["SR_B5", "SR_B6"]).rename("NDMI")
    lst_c = image.select("ST_B10").multiply(0.00341802).add(149.0).subtract(273.15).rename("LST_C")
    return ndvi.addBands(ndmi).addBands(lst_c).updateMask(mask).copyProperties(image, image.propertyNames())


def extract_landsat(geometry, start_date: str, end_date: str) -> dict:
    name = "landsat"
    if not _EE_READY:
        return _dataset_result(name, "auth_required", message=f"Earth Engine authentication required: {_EE_AUTH_ERROR}")
    l8 = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
    l9 = ee.ImageCollection("LANDSAT/LC09/C02/T1_L2")
    collection = l8.merge(l9).filterBounds(geometry).filterDate(start_date, end_date)
    total = int(collection.size().getInfo())
    if total == 0:
        return _dataset_result(name, "no_data", message="No Landsat 8/9 scenes intersect this AOI/date range.")
    rows = _monthly_reduce(collection, geometry, start_date, end_date, 30, ["NDVI", "NDMI", "LST_C"], "mean", image_mapper=_prepare_landsat)
    has_values = any(any(r.get(k) is not None for k in ("NDVI", "NDMI", "LST_C")) for r in rows)
    return _dataset_result(
        name, "ok" if has_values else "no_data",
        records=rows,
        metadata={"image_count_in_period": total, "reduction_scale_m": 30, "scale_factors_applied": True}
    )


def extract_grace(geometry, start_date: str, end_date: str) -> dict:
    name = "grace"
    if not _EE_READY:
        return _dataset_result(name, "auth_required", message=f"Earth Engine authentication required: {_EE_AUTH_ERROR}")
    collection = (
        ee.ImageCollection(DATASET_CATALOG[name]["earth_engine_id"])
        .filterBounds(geometry)
        .filterDate(start_date, end_date)
        .select("lwe_thickness")
    )
    total = int(collection.size().getInfo())
    if total == 0:
        return _dataset_result(name, "no_data", message="No GRACE/GRACE-FO Mascon images intersect this AOI/date range.")
    rows = _monthly_reduce(collection, geometry, start_date, end_date, 55660, ["lwe_thickness"], "mean")
    has_values = any(r.get("lwe_thickness") is not None for r in rows)
    return _dataset_result(
        name, "ok" if has_values else "no_data",
        records=rows,
        metadata={"image_count_in_period": total, "reduction_scale_m": 55660}
    )


def _mask_ecostress(image):
    qc = image.select("QC")
    good = qc.bitwiseAnd(1).eq(0)
    good = good.And(qc.bitwiseAnd(8).eq(0))
    good = good.And(qc.bitwiseAnd(16).eq(0))
    good = good.And(qc.bitwiseAnd(64).eq(0))
    good = good.And(qc.bitwiseAnd(128).eq(0))
    lst_c = image.select("LST").subtract(273.15).rename("LST_C")
    return lst_c.updateMask(good).copyProperties(image, image.propertyNames())


def extract_ecostress(geometry, start_date: str, end_date: str) -> dict:
    name = "ecostress"
    if not _EE_READY:
        return _dataset_result(name, "auth_required", message=f"Earth Engine authentication required: {_EE_AUTH_ERROR}")
    collection = (
        ee.ImageCollection(DATASET_CATALOG[name]["earth_engine_id"])
        .filterBounds(geometry)
        .filterDate(start_date, end_date)
    )
    total = int(collection.size().getInfo())
    if total == 0:
        return _dataset_result(
            name, "no_data",
            message="No ECOSTRESS images intersect this AOI/date range. Catalog contains limited global tiles."
        )
    rows = _monthly_reduce(collection, geometry, start_date, end_date, 70, ["LST_C"], "mean", image_mapper=_mask_ecostress)
    has_values = any(r.get("LST_C") is not None for r in rows)
    return _dataset_result(
        name, "ok" if has_values else "no_data",
        records=rows,
        metadata={"image_count_in_period": total, "reduction_scale_m": 70}
    )


def extract_srtm(geometry) -> dict:
    name = "srtm"
    if not _EE_READY:
        return _dataset_result(name, "auth_required", message=f"Earth Engine authentication required: {_EE_AUTH_ERROR}")
    elevation = ee.Image("USGS/SRTMGL1_003").select("elevation").rename("elevation_m")
    slope = ee.Terrain.slope(elevation).rename("slope_deg")
    image = elevation.addBands(slope)
    reducer = (
        ee.Reducer.mean()
        .combine(ee.Reducer.min(), sharedInputs=True)
        .combine(ee.Reducer.max(), sharedInputs=True)
    )
    stats = image.reduceRegion(
        reducer=reducer,
        geometry=geometry,
        scale=90,
        maxPixels=1e13,
        bestEffort=True,
        tileScale=4,
    ).getInfo() or {}
    has_values = any(v is not None for v in stats.values())
    if not has_values:
        return _dataset_result(name, "no_data", message="SRTM has no valid pixels for this AOI.")
    return _dataset_result(name, "ok", records=[{"period": "static", **stats}], metadata={"reduction_scale_m": 90})


def extract_nasa_power(centroid_lon: float, centroid_lat: float, start_date: str, end_date: str) -> dict:
    """
    Query official NASA POWER Agroclimatology REST API.
    Does not require Earth Engine authentication; uses public NASA REST endpoint.
    """
    name = "nasa_power"
    api_end = (pd.Timestamp(end_date) - pd.Timedelta(days=1)).strftime("%Y%m%d")
    api_start = pd.Timestamp(start_date).strftime("%Y%m%d")
    if api_end < api_start:
        return _dataset_result(name, "no_data", message="Empty NASA POWER date interval.")

    url = "https://power.larc.nasa.gov/api/temporal/daily/point"
    params = {
        "parameters": "PRECTOTCORR,T2M,RH2M,ALLSKY_SFC_SW_DWN",
        "community": "AG",
        "longitude": float(centroid_lon),
        "latitude": float(centroid_lat),
        "start": api_start,
        "end": api_end,
        "format": "JSON",
        "time-standard": "UTC",
    }

    response_json = None
    last_error = None
    for attempt in range(3):
        try:
            response = requests.get(url, params=params, timeout=(15, 60))
            if response.status_code == 200:
                response_json = response.json()
                break
            else:
                last_error = f"HTTP {response.status_code}: {response.text[:200]}"
        except Exception as exc:
            last_error = exc
            time.sleep(1.0 * (attempt + 1))

    if response_json is None:
        logger.warning("NASA POWER request failed: %s", last_error)
        return _dataset_result(name, "error", message=f"NASA POWER API unreachable: {last_error}")

    parameter_data = response_json.get("properties", {}).get("parameter", {})
    if not parameter_data:
        return _dataset_result(name, "no_data", message="NASA POWER returned no parameter data.")

    daily = pd.DataFrame(parameter_data)
    daily.index = pd.to_datetime(daily.index.astype(str), format="%Y%m%d", errors="coerce")
    daily = daily.loc[~daily.index.isna()]
    daily = daily.apply(pd.to_numeric, errors="coerce").replace([-999, -999.0], np.nan)
    if daily.empty:
        return _dataset_result(name, "no_data", message="NASA POWER returned no valid numeric rows.")

    monthly_rows = []
    grouped = daily.resample("MS")
    for period_start, group in grouped:
        record = {
            "period": period_start.strftime("%Y-%m"),
            "daily_record_count": int(group.notna().any(axis=1).sum()),
        }
        if "PRECTOTCORR" in group:
            record["PRECTOTCORR_monthly_sum"] = (
                float(group["PRECTOTCORR"].sum(min_count=1))
                if group["PRECTOTCORR"].notna().any() else None
            )
        for col in ("T2M", "RH2M", "ALLSKY_SFC_SW_DWN"):
            if col in group:
                record[f"{col}_monthly_mean"] = (
                    float(group[col].mean())
                    if group[col].notna().any() else None
                )
        monthly_rows.append(record)

    has_values = any(r.get("daily_record_count", 0) > 0 for r in monthly_rows)
    return _dataset_result(
        name, "ok" if has_values else "no_data",
        records=monthly_rows,
        metadata={
            "sampling_method": "NASA POWER daily agroclimatology grid point at AOI centroid",
            "centroid_longitude": float(centroid_lon),
            "centroid_latitude": float(centroid_lat),
            "source_api": url,
        }
    )


def build_analysis_summary(dataset_results: dict) -> dict:
    """Summarize latest satellite metrics across datasets."""
    summary = {}
    gpm_rows = dataset_results.get("gpm", {}).get("records", [])
    gpm_values = [r.get("rainfall_mm") for r in gpm_rows if isinstance(r.get("rainfall_mm"), (int, float))]
    if gpm_values:
        summary["gpm_total_rainfall_mm_over_period"] = float(sum(gpm_values))

    for dataset_name, field, summary_key in (
        ("smap", "sm_surface", "latest_smap_surface_soil_moisture_m3_m3"),
        ("smap", "sm_rootzone", "latest_smap_rootzone_soil_moisture_m3_m3"),
        ("modis", "NDVI", "latest_modis_ndvi"),
        ("modis", "EVI", "latest_modis_evi"),
        ("landsat", "NDVI", "latest_landsat_ndvi"),
        ("landsat", "NDMI", "latest_landsat_ndmi"),
        ("landsat", "LST_C", "latest_landsat_land_surface_temp_c"),
        ("grace", "lwe_thickness", "latest_grace_water_storage_anomaly_cm"),
        ("ecostress", "LST_C", "latest_ecostress_land_surface_temp_c"),
    ):
        rows = dataset_results.get(dataset_name, {}).get("records", [])
        valid = [r for r in rows if r.get(field) is not None]
        if valid:
            summary[summary_key] = valid[-1].get(field)
            summary[f"{summary_key}_period"] = valid[-1].get("period")

    # NASA POWER fallback for temperature and precipitation
    power_rows = dataset_results.get("nasa_power", {}).get("records", [])
    valid_power = [r for r in power_rows if r.get("T2M_monthly_mean") is not None]
    if valid_power:
        summary["latest_nasa_power_temp_c"] = valid_power[-1].get("T2M_monthly_mean")
        summary["latest_nasa_power_rainfall_mm"] = valid_power[-1].get("PRECTOTCORR_monthly_sum")
        summary["latest_nasa_power_period"] = valid_power[-1].get("period")

    srtm_rows = dataset_results.get("srtm", {}).get("records", [])
    if srtm_rows:
        for field in ("elevation_m_mean", "elevation_m_min", "elevation_m_max", "slope_deg_mean"):
            if srtm_rows[0].get(field) is not None:
                summary[field] = srtm_rows[0][field]
    return summary


def run_farm_analysis(
    geometry_geojson: dict,
    start_date: str = DEFAULT_START_DATE,
    end_date: Optional[str] = None,
    datasets: Optional[List[str]] = None,
    location_id: str = "farm-1",
    location_name: str = "Farm",
    centroid_lat: Optional[float] = None,
    centroid_lon: Optional[float] = None
) -> dict:
    """
    Main execution service. Extracts requested NASA Earth observation datasets.
    """
    global _EE_READY
    if not _EE_READY:
        initialize_earth_engine()

    if end_date is None:
        end_date = pd.Timestamp.now(tz="UTC").normalize().replace(day=1).strftime("%Y-%m-%d")

    requested_datasets = datasets or list(SUPPORTED_DATASETS)

    # Determine centroid
    lat = centroid_lat or 17.385
    lon = centroid_lon or 78.487
    geom_type = geometry_geojson.get("type", "Point")

    ee_geom = None
    if _EE_READY and ee is not None:
        try:
            if geom_type in ("Point", "MultiPoint", "LineString", "MultiLineString"):
                ee_geom = ee.Geometry(geometry_geojson).buffer(5000)
            else:
                ee_geom = ee.Geometry(geometry_geojson, proj="EPSG:4326", geodesic=False)
            c_coords = ee_geom.centroid(maxError=10).coordinates().getInfo()
            lon, lat = float(c_coords[0]), float(c_coords[1])
        except Exception as e:
            logger.warning("Could not construct EE geometry: %s", e)
            ee_geom = None

    dataset_results = {}
    warnings = []
    errors = []

    for name in requested_datasets:
        if name not in SUPPORTED_DATASETS:
            continue
        try:
            if name == "nasa_power":
                res = extract_nasa_power(lon, lat, start_date, end_date)
            elif name == "srtm":
                if ee_geom is not None and _EE_READY:
                    res = extract_srtm(ee_geom)
                else:
                    res = _dataset_result(name, "auth_required", message=f"Earth Engine not initialized ({_EE_AUTH_ERROR})")
            elif name == "smap":
                if ee_geom is not None and _EE_READY:
                    res = extract_smap(ee_geom, start_date, end_date)
                else:
                    res = _dataset_result(name, "auth_required", message=f"Earth Engine not initialized ({_EE_AUTH_ERROR})")
            elif name == "gpm":
                if ee_geom is not None and _EE_READY:
                    res = extract_gpm(ee_geom, start_date, end_date)
                else:
                    res = _dataset_result(name, "auth_required", message=f"Earth Engine not initialized ({_EE_AUTH_ERROR})")
            elif name == "modis":
                if ee_geom is not None and _EE_READY:
                    res = extract_modis(ee_geom, start_date, end_date)
                else:
                    res = _dataset_result(name, "auth_required", message=f"Earth Engine not initialized ({_EE_AUTH_ERROR})")
            elif name == "landsat":
                if ee_geom is not None and _EE_READY:
                    res = extract_landsat(ee_geom, start_date, end_date)
                else:
                    res = _dataset_result(name, "auth_required", message=f"Earth Engine not initialized ({_EE_AUTH_ERROR})")
            elif name == "grace":
                if ee_geom is not None and _EE_READY:
                    res = extract_grace(ee_geom, start_date, end_date)
                else:
                    res = _dataset_result(name, "auth_required", message=f"Earth Engine not initialized ({_EE_AUTH_ERROR})")
            elif name == "ecostress":
                if ee_geom is not None and _EE_READY:
                    res = extract_ecostress(ee_geom, start_date, end_date)
                else:
                    res = _dataset_result(name, "auth_required", message=f"Earth Engine not initialized ({_EE_AUTH_ERROR})")
            else:
                res = _dataset_result(name, "error", message="Unsupported dataset")

            dataset_results[name] = json_safe(res)
            if res.get("status") in ("no_data", "auth_required"):
                warnings.append(f"{name}: {res.get('message')}")
        except Exception as exc:
            logger.exception("Failed extracting dataset %s: %s", name, exc)
            err_dict = _dataset_result(name, "error", message=str(exc))
            dataset_results[name] = json_safe(err_dict)
            errors.append({"dataset": name, "error": str(exc)})

    ok_count = sum(1 for x in dataset_results.values() if x.get("status") == "ok")

    response = {
        "ok": ok_count > 0,
        "request_id": str(uuid.uuid4()),
        "farm_id": location_id,
        "aoi": {
            "location_id": location_id,
            "location_name": location_name,
            "geometry_type": geom_type,
            "centroid": {"latitude": lat, "longitude": lon},
        },
        "period": {
            "start_date": start_date,
            "end_date": end_date,
        },
        "datasets": dataset_results,
        "summary": build_analysis_summary(dataset_results),
        "warnings": warnings,
        "errors": errors,
        "integration": {
            "response_version": "1.0",
            "coordinate_system": "EPSG:4326",
            "earth_engine_status": get_earth_engine_status(),
        }
    }
    return json_safe(response)
