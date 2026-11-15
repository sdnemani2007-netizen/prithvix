# Generated from PrithviX_Global.ipynb. Keep these definitions in sync.

# =============================================================================
# PrithviX Global NASA Data Pipeline
# Backend-safe core: accepts a GeoJSON geometry from the frontend and returns
# JSON-serializable monthly data + AOI metadata.
# =============================================================================

import os
import re
import json
import uuid
import math
import time
import zipfile
import logging
from pathlib import Path
from datetime import datetime, timezone, date
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import requests
import ee

logger = logging.getLogger("prithvix")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

EE_PROJECT = os.environ.get("EE_PROJECT", "prithvix-514718")
DEFAULT_START_DATE = "2021-01-01"
MAX_ANALYSIS_MONTHS = 120

# These are included as optional modules in the pipeline. A dataset can return
# no_data for a location/date without failing the other requested datasets.
SUPPORTED_DATASETS = (
    "smap", "gpm", "modis", "landsat", "nasa_power",
    "srtm", "grace", "ecostress"
)
DEFAULT_DATASETS = list(SUPPORTED_DATASETS)

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


def initialize_earth_engine(interactive_auth: bool = False,
                            project_id: Optional[str] = None) -> None:
    """
    Initialize Earth Engine.

    Colab: run initialize_earth_engine(interactive_auth=True) once after
    installing packages. Backend/Cloud Run: configure Application Default
    Credentials for the backend service account and call with False.
    """
    global _EE_READY
    project = project_id or EE_PROJECT
    try:
        ee.Initialize(project=project)
        _EE_READY = True
        logger.info("Earth Engine initialized with project %s", project)
        return
    except Exception as first_error:
        if interactive_auth:
            try:
                ee.Authenticate()
                ee.Initialize(project=project)
                _EE_READY = True
                logger.info("Earth Engine authenticated and initialized.")
                return
            except Exception as second_error:
                raise RuntimeError(
                    "Earth Engine initialization failed. Confirm that this "
                    "Google account has Earth Engine access and that the "
                    f"Cloud project '{project}' is registered/enabled. "
                    f"Original error: {first_error}; authentication error: "
                    f"{second_error}"
                ) from second_error
        raise RuntimeError(
            "Earth Engine initialization failed. On Colab, authenticate once "
            "with initialize_earth_engine(interactive_auth=True). On a hosted "
            "backend, configure Application Default Credentials and grant the "
            f"runtime service account Earth Engine access. Project: {project}. "
            f"Original error: {first_error}"
        ) from first_error


_EE_READY = False


def _coordinate_positions(value):
    """Yield GeoJSON coordinate pairs recursively."""
    if isinstance(value, (list, tuple)):
        if (len(value) >= 2 and
                isinstance(value[0], (int, float)) and
                isinstance(value[1], (int, float))):
            yield float(value[0]), float(value[1])
        else:
            for child in value:
                yield from _coordinate_positions(child)


def _extract_geometry_object(aoi_geojson: dict) -> dict:
    """Accept a GeoJSON Geometry, Feature, or non-empty FeatureCollection."""
    if not isinstance(aoi_geojson, dict):
        raise ValueError("aoi_geojson must be a GeoJSON object (dictionary).")

    obj_type = aoi_geojson.get("type")
    if obj_type == "Feature":
        geometry = aoi_geojson.get("geometry")
        if not isinstance(geometry, dict):
            raise ValueError("GeoJSON Feature has no valid geometry.")
        return geometry

    if obj_type == "FeatureCollection":
        features = aoi_geojson.get("features")
        if not isinstance(features, list) or not features:
            raise ValueError("GeoJSON FeatureCollection must contain features.")
        geometries = [
            f.get("geometry") for f in features
            if isinstance(f, dict) and isinstance(f.get("geometry"), dict)
        ]
        if not geometries:
            raise ValueError("FeatureCollection contains no valid geometries.")
        # Earth Engine accepts FeatureCollection GeoJSON, but returning a
        # GeometryCollection avoids relying on feature properties.
        return {"type": "GeometryCollection", "geometries": geometries}

    if obj_type in (
        "Point", "MultiPoint", "LineString", "MultiLineString",
        "Polygon", "MultiPolygon", "GeometryCollection"
    ):
        return aoi_geojson

    raise ValueError(
        "Unsupported GeoJSON type. Send Point, Polygon, MultiPolygon, "
        "LineString, MultiLineString, MultiPoint, GeometryCollection, "
        "Feature, or FeatureCollection."
    )


def validate_request(payload: dict) -> dict:
    """
    Validate and normalize a frontend request without contacting Earth Engine.

    Required:
      - aoi_geojson (GeoJSON Geometry/Feature/FeatureCollection) OR bbox
      - start_date, end_date (YYYY-MM-DD; end_date is exclusive)

    Optional:
      - location_id, location_name, datasets, point_buffer_m
    """
    if not isinstance(payload, dict):
        raise ValueError("Request body must be a JSON object.")

    request = dict(payload)

    if "aoi_geojson" not in request and "bbox" not in request:
        raise ValueError("Send aoi_geojson or bbox from the map selection.")

    if "bbox" in request and "aoi_geojson" not in request:
        bbox = request["bbox"]
        if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
            raise ValueError("bbox must be [west, south, east, north].")
        west, south, east, north = [float(x) for x in bbox]
        if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
            raise ValueError("bbox coordinates are outside valid WGS84 ranges.")
        request["aoi_geojson"] = {
            "type": "Polygon",
            "coordinates": [[
                [west, south], [east, south], [east, north],
                [west, north], [west, south]
            ]]
        }

    geometry = _extract_geometry_object(request["aoi_geojson"])
    positions = list(_coordinate_positions(geometry.get("coordinates", [])))
    if geometry.get("type") == "GeometryCollection":
        for item in geometry.get("geometries", []):
            positions.extend(list(_coordinate_positions(item.get("coordinates", []))))
    if not positions:
        raise ValueError("GeoJSON geometry contains no coordinate positions.")
    for lon, lat in positions:
        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
            raise ValueError(
                "GeoJSON coordinates must be WGS84 longitude/latitude "
                "in the ranges [-180, 180] and [-90, 90]."
            )

    point_buffer_m = float(request.get("point_buffer_m", 5000))
    if not (1 <= point_buffer_m <= 100000):
        raise ValueError("point_buffer_m must be between 1 and 100000 metres.")

    start_value = request.get("start_date", DEFAULT_START_DATE)
    end_value = request.get("end_date")
    if end_value is None:
        now_utc = pd.Timestamp.now(tz="UTC")
        end_value = now_utc.normalize().replace(day=1).strftime("%Y-%m-%d")

    try:
        start_ts = pd.Timestamp(start_value)
        end_ts = pd.Timestamp(end_value)
        if start_ts.tzinfo is not None:
            start_ts = start_ts.tz_convert("UTC").tz_localize(None)
        if end_ts.tzinfo is not None:
            end_ts = end_ts.tz_convert("UTC").tz_localize(None)
        start_ts = start_ts.normalize()
        end_ts = end_ts.normalize()
    except Exception as exc:
        raise ValueError("start_date and end_date must be valid YYYY-MM-DD dates.") from exc

    if pd.isna(start_ts) or pd.isna(end_ts):
        raise ValueError("start_date and end_date must be valid dates.")
    if start_ts >= end_ts:
        raise ValueError("start_date must be earlier than end_date.")
    today_utc = pd.Timestamp.now(tz="UTC").normalize().tz_localize(None)
    if end_ts > today_utc + pd.Timedelta(days=1):
        raise ValueError("end_date cannot be in the future.")
    months = len(pd.period_range(start_ts, end_ts - pd.Timedelta(days=1), freq="M"))
    if months > MAX_ANALYSIS_MONTHS:
        raise ValueError(
            f"Requested {months} months. The synchronous analysis limit is "
            f"{MAX_ANALYSIS_MONTHS} months per request; split longer periods."
        )

    datasets = request.get("datasets", DEFAULT_DATASETS)
    if not isinstance(datasets, list) or not datasets:
        raise ValueError("datasets must be a non-empty list of supported names.")
    datasets = list(dict.fromkeys(str(x).strip().lower() for x in datasets))
    unknown = sorted(set(datasets) - set(SUPPORTED_DATASETS))
    if unknown:
        raise ValueError(
            f"Unknown dataset(s): {unknown}. Supported: {list(SUPPORTED_DATASETS)}"
        )

    request["aoi_geojson"] = geometry
    request["point_buffer_m"] = point_buffer_m
    request["start_date"] = start_ts.strftime("%Y-%m-%d")
    request["end_date"] = end_ts.strftime("%Y-%m-%d")
    request["datasets"] = datasets
    request["location_id"] = str(request.get("location_id") or uuid.uuid4())
    request["location_name"] = str(request.get("location_name") or "Map-selected area")
    return request


def build_earth_engine_geometry(request: dict):
    """Convert validated WGS84 GeoJSON to an Earth Engine geometry."""
    geometry_json = request["aoi_geojson"]
    geometry_type = geometry_json.get("type")

    geometry = ee.Geometry(
        geometry_json, proj="EPSG:4326", geodesic=False
    )
    # A map click or drawn line has zero area. Buffer it so area-based
    # reducers can sample the surrounding Earth observation pixels.
    if geometry_type in ("Point", "MultiPoint", "LineString", "MultiLineString"):
        geometry = geometry.buffer(request["point_buffer_m"])
    return geometry


def _month_windows(start_date: str, end_date: str) -> List[dict]:
    """Create partial-month-safe windows; end_date is exclusive."""
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


def _feature_collection_records(feature_collection) -> List[dict]:
    """Materialize a small monthly FeatureCollection into plain Python rows."""
    info = feature_collection.getInfo()
    rows = []
    for feature in info.get("features", []):
        rows.append(feature.get("properties", {}))
    return rows


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
    """
    Build one Earth Engine feature per month and make one getInfo call.

    For sum collections, input images must already be converted to per-image
    amounts/units before this function is called.
    """
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
    return _feature_collection_records(ee.FeatureCollection(features))


def _dataset_result(name: str, status: str, records=None, message=None,
                    metadata=None) -> dict:
    result = {
        "status": status,
        "source": DATASET_CATALOG[name]["name"],
        "source_id": DATASET_CATALOG[name]["earth_engine_id"],
        "nominal_scale_m": DATASET_CATALOG[name]["nominal_scale_m"],
        "temporal_resolution": DATASET_CATALOG[name]["temporal_resolution"],
        "units": DATASET_CATALOG[name]["units"],
        "caveat": DATASET_CATALOG[name]["caveat"],
        "records": records or [],
        "message": message,
    }
    if metadata:
        result["metadata"] = metadata
    return result


def extract_smap(geometry, start_date: str, end_date: str) -> dict:
    name = "smap"
    collection = (
        ee.ImageCollection(DATASET_CATALOG[name]["earth_engine_id"])
        .filterBounds(geometry)
        .filterDate(start_date, end_date)
        .select(["sm_surface", "sm_rootzone"])
    )
    total = int(collection.size().getInfo())
    if total == 0:
        return _dataset_result(name, "no_data", message="No SMAP images intersect this AOI/date range.")
    rows = _monthly_reduce(
        collection, geometry, start_date, end_date, 11000,
        ["sm_surface", "sm_rootzone"], "mean"
    )
    return _dataset_result(
        name, "ok" if any(r.get("sm_surface") is not None or r.get("sm_rootzone") is not None for r in rows) else "no_data",
        records=rows, message=None if rows else "No monthly SMAP results.",
        metadata={"image_count_in_period": total, "reduction_scale_m": 11000}
    )


def _gpm_half_hour_to_mm(image):
    # Catalog unit is mm/hr; every image represents a 30-minute interval.
    return (
        image.select("precipitation")
        .multiply(0.5)
        .rename("rainfall_mm")
        .copyProperties(image, image.propertyNames())
    )


def extract_gpm(geometry, start_date: str, end_date: str) -> dict:
    name = "gpm"
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
    return _dataset_result(
        name, "ok" if any(r.get("rainfall_mm") is not None for r in rows) else "no_data",
        records=rows,
        metadata={
            "image_count_in_period": total,
            "reduction_scale_m": 11132,
            "calculation": "sum(precipitation_mm_per_hour * 0.5 hour), then AOI mean",
        }
    )


def _mask_and_scale_modis(image):
    qa = image.select("DetailedQA")
    # Retain MODLAND quality 0 or 1; drop cloudy/no-production QA classes 2/3.
    good_quality = qa.bitwiseAnd(3).lte(1)
    scaled = image.select(["NDVI", "EVI"]).multiply(0.0001)
    return scaled.updateMask(good_quality).copyProperties(
        image, image.propertyNames()
    )


def extract_modis(geometry, start_date: str, end_date: str) -> dict:
    name = "modis"
    collection = (
        ee.ImageCollection(DATASET_CATALOG[name]["earth_engine_id"])
        .filterBounds(geometry)
        .filterDate(start_date, end_date)
    )
    total = int(collection.size().getInfo())
    if total == 0:
        return _dataset_result(name, "no_data", message="No MODIS vegetation-index images intersect this AOI/date range.")
    rows = _monthly_reduce(
        collection, geometry, start_date, end_date, 250,
        ["NDVI", "EVI"], "mean", image_mapper=_mask_and_scale_modis
    )
    return _dataset_result(
        name, "ok" if any(r.get("NDVI") is not None or r.get("EVI") is not None for r in rows) else "no_data",
        records=rows,
        metadata={"image_count_in_period": total, "reduction_scale_m": 250, "qa_rule": "DetailedQA bits 0-1 <= 1"}
    )


def _prepare_landsat(image):
    qa = image.select("QA_PIXEL")
    # Mask fill, dilated cloud, cirrus, cloud, cloud shadow, and snow.
    mask = qa.bitwiseAnd(1 << 0).eq(0)
    for bit in (1, 2, 3, 4, 5):
        mask = mask.And(qa.bitwiseAnd(1 << bit).eq(0))
    # Saturated pixels are excluded as well.
    mask = mask.And(image.select("QA_RADSAT").eq(0))

    sr = (
        image.select(["SR_B4", "SR_B5", "SR_B6"])
        .multiply(0.0000275)
        .add(-0.2)
    )
    ndvi = sr.normalizedDifference(["SR_B5", "SR_B4"]).rename("NDVI")
    ndmi = sr.normalizedDifference(["SR_B5", "SR_B6"]).rename("NDMI")
    lst_c = (
        image.select("ST_B10")
        .multiply(0.00341802)
        .add(149.0)
        .subtract(273.15)
        .rename("LST_C")
    )
    return ndvi.addBands(ndmi).addBands(lst_c).updateMask(mask).copyProperties(
        image, image.propertyNames()
    )


def extract_landsat(geometry, start_date: str, end_date: str) -> dict:
    name = "landsat"
    l8 = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
    l9 = ee.ImageCollection("LANDSAT/LC09/C02/T1_L2")
    collection = (
        l8.merge(l9)
        .filterBounds(geometry)
        .filterDate(start_date, end_date)
    )
    total = int(collection.size().getInfo())
    if total == 0:
        return _dataset_result(name, "no_data", message="No Landsat 8/9 scenes intersect this AOI/date range.")
    rows = _monthly_reduce(
        collection, geometry, start_date, end_date, 30,
        ["NDVI", "NDMI", "LST_C"], "mean", image_mapper=_prepare_landsat
    )
    return _dataset_result(
        name, "ok" if any(
            any(r.get(k) is not None for k in ("NDVI", "NDMI", "LST_C"))
            for r in rows
        ) else "no_data",
        records=rows,
        metadata={
            "image_count_in_period": total,
            "reduction_scale_m": 30,
            "qa_rule": "QA_PIXEL bits 0-5 and QA_RADSAT == 0",
            "scale_factors_applied": True,
        }
    )


def extract_grace(geometry, start_date: str, end_date: str) -> dict:
    name = "grace"
    collection = (
        ee.ImageCollection(DATASET_CATALOG[name]["earth_engine_id"])
        .filterBounds(geometry)
        .filterDate(start_date, end_date)
        .select("lwe_thickness")
    )
    total = int(collection.size().getInfo())
    if total == 0:
        return _dataset_result(name, "no_data", message="No GRACE/GRACE-FO Mascon images intersect this AOI/date range.")
    rows = _monthly_reduce(
        collection, geometry, start_date, end_date, 55660,
        ["lwe_thickness"], "mean"
    )
    return _dataset_result(
        name, "ok" if any(r.get("lwe_thickness") is not None for r in rows) else "no_data",
        records=rows,
        metadata={
            "image_count_in_period": total,
            "reduction_scale_m": 55660,
            "interpretation": "Equivalent water thickness anomaly, not absolute groundwater depth",
        }
    )


def _mask_ecostress(image):
    qc = image.select("QC")
    good = qc.bitwiseAnd(1).eq(0)       # Good LST quality
    good = good.And(qc.bitwiseAnd(8).eq(0))    # Clear sky
    good = good.And(qc.bitwiseAnd(16).eq(0))   # Not an outlier
    good = good.And(qc.bitwiseAnd(64).eq(0))   # No snow/ice
    good = good.And(qc.bitwiseAnd(128).eq(0))  # Land
    lst_c = image.select("LST").subtract(273.15).rename("LST_C")
    return lst_c.updateMask(good).copyProperties(image, image.propertyNames())


def extract_ecostress(geometry, start_date: str, end_date: str) -> dict:
    name = "ecostress"
    collection = (
        ee.ImageCollection(DATASET_CATALOG[name]["earth_engine_id"])
        .filterBounds(geometry)
        .filterDate(start_date, end_date)
    )
    total = int(collection.size().getInfo())
    if total == 0:
        return _dataset_result(
            name, "no_data",
            message=(
                "No ECOSTRESS images intersect this AOI/date range. The current "
                "Earth Engine catalog says only Los Angeles metro tiles have "
                "been ingested; this is expected for most world locations."
            )
        )
    rows = _monthly_reduce(
        collection, geometry, start_date, end_date, 70,
        ["LST_C"], "mean", image_mapper=_mask_ecostress
    )
    return _dataset_result(
        name, "ok" if any(r.get("LST_C") is not None for r in rows) else "no_data",
        records=rows,
        metadata={
            "image_count_in_period": total,
            "reduction_scale_m": 70,
            "qa_rule": "QC good quality, clear sky, no outlier, no snow/ice, land pixels",
        }
    )


def extract_srtm(geometry) -> dict:
    name = "srtm"
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

    has_values = any(value is not None for value in stats.values())
    if not has_values:
        return _dataset_result(
            name, "no_data",
            message="SRTM has no valid pixels for this AOI (coverage is not global, especially at high polar latitudes)."
        )
    return _dataset_result(
        name, "ok",
        records=[{"period": "static", **stats}],
        metadata={"reduction_scale_m": 90, "source_pixel_size_m": 30}
    )


def extract_nasa_power(centroid_lon: float, centroid_lat: float,
                       start_date: str, end_date: str) -> dict:
    name = "nasa_power"
    # POWER daily endpoint uses inclusive YYYYMMDD end dates.
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
            response = requests.get(url, params=params, timeout=(15, 90))
            response.raise_for_status()
            response_json = response.json()
            break
        except Exception as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))
    if response_json is None:
        raise RuntimeError(f"NASA POWER request failed after 3 attempts: {last_error}")

    parameter_data = (
        response_json.get("properties", {}).get("parameter", {})
        if isinstance(response_json, dict) else {}
    )
    if not parameter_data:
        messages = response_json.get("messages", []) if isinstance(response_json, dict) else []
        raise RuntimeError(f"NASA POWER returned no parameter data. Messages: {messages}")

    daily = pd.DataFrame(parameter_data)
    daily.index = pd.to_datetime(daily.index.astype(str), format="%Y%m%d", errors="coerce")
    daily = daily.loc[~daily.index.isna()]
    daily = daily.apply(pd.to_numeric, errors="coerce").replace([-999, -999.0], np.nan)
    if daily.empty:
        return _dataset_result(name, "no_data", message="NASA POWER returned no daily rows.")

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
        for column in ("T2M", "RH2M", "ALLSKY_SFC_SW_DWN"):
            if column in group:
                record[f"{column}_monthly_mean"] = (
                    float(group[column].mean())
                    if group[column].notna().any() else None
                )
        monthly_rows.append(record)

    return _dataset_result(
        name, "ok" if monthly_rows and any(r["daily_record_count"] > 0 for r in monthly_rows) else "no_data",
        records=monthly_rows,
        metadata={
            "sampling_method": "NASA POWER daily grid point at AOI centroid",
            "centroid_longitude": float(centroid_lon),
            "centroid_latitude": float(centroid_lat),
            "daily_api_url": url,
            "time_standard": "UTC",
        }
    )


def _json_safe(value):
    """Convert NumPy/Pandas values to strict JSON-safe Python values."""
    if value is None:
        return None
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return float(value) if math.isfinite(float(value)) else None
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()
    if pd.isna(value):
        return None
    return value


def _build_summary(dataset_results: dict) -> dict:
    summary = {}
    gpm_rows = dataset_results.get("gpm", {}).get("records", [])
    gpm_values = [
        r.get("rainfall_mm") for r in gpm_rows
        if isinstance(r.get("rainfall_mm"), (int, float))
    ]
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

    srtm_rows = dataset_results.get("srtm", {}).get("records", [])
    if srtm_rows:
        for field in (
            "elevation_m_mean", "elevation_m_min", "elevation_m_max",
            "slope_deg_mean", "slope_deg_min", "slope_deg_max"
        ):
            if srtm_rows[0].get(field) is not None:
                summary[field] = srtm_rows[0][field]
    return summary


def run_analysis(payload: dict, auto_initialize: bool = True,
                 interactive_auth: bool = False) -> dict:
    """
    Main entry point for notebook, backend, or FastAPI.

    Args:
      payload: validated frontend JSON request.
      auto_initialize: initialize Earth Engine when required.
      interactive_auth: allow ee.Authenticate() (Colab only).

    Returns:
      JSON-serializable dictionary. Dataset-specific failures do not abort
      the other datasets; inspect each datasets[name].status/message.
    """
    global _EE_READY
    request = validate_request(payload)

    if auto_initialize and not _EE_READY:
        initialize_earth_engine(interactive_auth=interactive_auth)

    geometry = build_earth_engine_geometry(request)
    geometry_area_km2 = float(geometry.area(maxError=10).divide(1e6).getInfo())
    centroid = geometry.centroid(maxError=10).coordinates().getInfo()
    centroid_lon, centroid_lat = float(centroid[0]), float(centroid[1])

    aoi_meta = {
        "location_id": request["location_id"],
        "location_name": request["location_name"],
        "geometry_type": request["aoi_geojson"]["type"],
        "area_km2": geometry_area_km2,
        "centroid": {"longitude": centroid_lon, "latitude": centroid_lat},
        "point_buffer_m": request["point_buffer_m"] if request["aoi_geojson"]["type"] == "Point" else None,
        "coordinate_reference_system": "EPSG:4326 (WGS84)",
    }

    dataset_results = {}
    errors = []
    warnings = []

    extractors = {
        "smap": lambda: extract_smap(geometry, request["start_date"], request["end_date"]),
        "gpm": lambda: extract_gpm(geometry, request["start_date"], request["end_date"]),
        "modis": lambda: extract_modis(geometry, request["start_date"], request["end_date"]),
        "landsat": lambda: extract_landsat(geometry, request["start_date"], request["end_date"]),
        "nasa_power": lambda: extract_nasa_power(
            centroid_lon, centroid_lat, request["start_date"], request["end_date"]
        ),
        "srtm": lambda: extract_srtm(geometry),
        "grace": lambda: extract_grace(geometry, request["start_date"], request["end_date"]),
        "ecostress": lambda: extract_ecostress(geometry, request["start_date"], request["end_date"]),
    }

    for name in request["datasets"]:
        try:
            dataset_result = extractors[name]()
            dataset_results[name] = _json_safe(dataset_result)
            if dataset_result.get("status") == "no_data":
                warnings.append(f"{name}: {dataset_result.get('message') or 'No data for this AOI/date range.'}")
        except Exception as exc:
            logger.exception("Dataset %s extraction failed", name)
            dataset_results[name] = _dataset_result(
                name, "error", message=f"{type(exc).__name__}: {exc}"
            )
            errors.append({"dataset": name, "error": f"{type(exc).__name__}: {exc}"})

    ok_count = sum(1 for x in dataset_results.values() if x.get("status") == "ok")
    response = {
        "ok": ok_count > 0,
        "request_id": str(uuid.uuid4()),
        "aoi": aoi_meta,
        "period": {
            "start_date": request["start_date"],
            "end_date_exclusive": request["end_date"],
        },
        "datasets": dataset_results,
        "summary": _build_summary(dataset_results),
        "warnings": warnings,
        "errors": errors,
        "integration": {
            "response_version": "1.0",
            "coordinate_system": "EPSG:4326",
            "monthly_period_label": "YYYY-MM",
            "frontend_should_read": "datasets.<dataset>.records and summary",
        },
    }
    return _json_safe(response)


def save_analysis_files(result: dict, output_dir: str = "prithvix_output") -> dict:
    """Save strict JSON, one CSV per dataset, and a ZIP bundle."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    json_path = output_path / "prithvix_response.json"
    with json_path.open("w", encoding="utf-8") as file:
        json.dump(_json_safe(result), file, indent=2, ensure_ascii=False, allow_nan=False)

    csv_paths = []
    for name, dataset in result.get("datasets", {}).items():
        records = dataset.get("records", [])
        frame = pd.DataFrame(records)
        csv_path = output_path / f"{name}.csv"
        frame.to_csv(csv_path, index=False)
        csv_paths.append(csv_path)

    zip_path = output_path / "prithvix_export_bundle.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(json_path, arcname=json_path.name)
        for csv_path in csv_paths:
            archive.write(csv_path, arcname=f"csv/{csv_path.name}")

    return {
        "json": str(json_path.resolve()),
        "zip": str(zip_path.resolve()),
        "csv_files": [str(p.resolve()) for p in csv_paths],
    }


def create_fastapi_app():
    """
    Optional REST adapter. Import this module in your backend, then run:
      uvicorn PrithviX_pipeline:app --host 0.0.0.0 --port 8000

    Configure Earth Engine credentials on the SERVER, never in the browser.
    Configure PRITHVIX_CORS_ORIGINS as a comma-separated allow-list.
    """
    from fastapi import FastAPI, HTTPException
    from starlette.concurrency import run_in_threadpool
    from fastapi.middleware.cors import CORSMiddleware

    app = FastAPI(
        title="PrithviX Geospatial API",
        version="1.0.0",
        description="Extract NASA Earth observation and climate data for map-selected AOIs."
    )
    origins = [
        x.strip() for x in os.environ.get("PRITHVIX_CORS_ORIGINS", "").split(",")
        if x.strip()
    ]
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=False,
            allow_methods=["GET", "POST"],
            allow_headers=["Content-Type", "Authorization"],
        )

    @app.get("/health")
    async def health():
        return {"status": "ok", "service": "PrithviX Geospatial API"}

    @app.get("/api/datasets")
    async def list_datasets():
        return {
            name: {
                "name": DATASET_CATALOG[name]["name"],
                "source_id": DATASET_CATALOG[name]["earth_engine_id"],
                "nominal_scale_m": DATASET_CATALOG[name]["nominal_scale_m"],
                "caveat": DATASET_CATALOG[name]["caveat"],
            }
            for name in SUPPORTED_DATASETS
        }

    @app.post("/api/analyze")
    async def analyze(payload: dict):
        try:
            # Earth Engine / network calls are blocking; run off the event loop.
            return await run_in_threadpool(run_analysis, payload, True, False)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception as exc:
            logger.exception("Request failed")
            raise HTTPException(
                status_code=500,
                detail=f"Analysis failed: {type(exc).__name__}: {exc}"
            ) from exc

    return app

# Uvicorn entry point: uvicorn PrithviX_pipeline:app --host 0.0.0.0 --port 8000
app = create_fastapi_app()
