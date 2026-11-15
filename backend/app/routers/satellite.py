import json
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.database import get_db
from app.models.farm import Farm
from app.schemas.satellite import SatelliteAnalysisResponse, DatasetMetadata
from app.schemas.analysis import SoilClimateResponse
from app.services import farm_service, earth_engine
from app.utils.geo import parse_boundary_to_geojson

router = APIRouter(tags=["Satellite Data"])


@router.get("/api/datasets")
def list_datasets():
    """List all supported NASA and Earth observation datasets."""
    return {
        name: {
            "name": entry["name"],
            "source_id": entry["earth_engine_id"],
            "nominal_scale_m": entry["nominal_scale_m"],
            "temporal_resolution": entry["temporal_resolution"],
            "units": entry["units"],
            "caveat": entry["caveat"],
        }
        for name, entry in earth_engine.DATASET_CATALOG.items()
    }


@router.get("/api/datasets/status")
def datasets_status():
    """Check Earth Engine credentials and service availability."""
    return earth_engine.get_earth_engine_status()


@router.get("/api/satellite/{farm_id}", response_model=SatelliteAnalysisResponse)
async def get_farm_satellite_data(
    farm_id: str,
    start_date: Optional[str] = "2023-01-01",
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Retrieve full NASA satellite extraction for a specific farm."""
    farm = farm_service.get_farm_by_id(db, farm_id)
    if not farm:
        raise HTTPException(status_code=404, detail=f"Farm '{farm_id}' not found.")

    geom = parse_boundary_to_geojson(
        json.loads(farm.boundary_geojson) if farm.boundary_geojson else None,
        farm.latitude,
        farm.longitude
    )

    result = await run_in_threadpool(
        earth_engine.run_farm_analysis,
        geometry_geojson=geom,
        start_date=start_date,
        end_date=end_date,
        location_id=farm.id,
        location_name=farm.name,
        centroid_lat=farm.latitude,
        centroid_lon=farm.longitude
    )
    return result


@router.get("/api/satellite/{farm_id}/timeseries", response_model=SoilClimateResponse)
async def get_farm_timeseries(
    farm_id: str,
    months: int = 12,
    db: Session = Depends(get_db)
):
    """
    Retrieve monthly time series for soil moisture, rainfall, surface temp,
    and vegetation NDVI for the Soil & Climate page.
    """
    farm = farm_service.get_farm_by_id(db, farm_id)
    if not farm:
        raise HTTPException(status_code=404, detail=f"Farm '{farm_id}' not found.")

    import pandas as pd
    end_dt = pd.Timestamp.now(tz="UTC").normalize().replace(day=1)
    start_dt = end_dt - pd.DateOffset(months=months)

    geom = parse_boundary_to_geojson(
        json.loads(farm.boundary_geojson) if farm.boundary_geojson else None,
        farm.latitude,
        farm.longitude
    )

    analysis = await run_in_threadpool(
        earth_engine.run_farm_analysis,
        geometry_geojson=geom,
        start_date=start_dt.strftime("%Y-%m-%d"),
        end_date=end_dt.strftime("%Y-%m-%d"),
        location_id=farm.id,
        location_name=farm.name,
        centroid_lat=farm.latitude,
        centroid_lon=farm.longitude,
        datasets=["smap", "gpm", "landsat", "modis", "nasa_power"]
    )

    datasets = analysis.get("datasets", {})

    periods = []
    moist_series = []
    rain_series = []
    lst_series = []
    ndvi_series = []

    # Prefer NASA POWER or GPM for timeline periods
    power_records = datasets.get("nasa_power", {}).get("records", [])
    smap_records = {r.get("period"): r for r in datasets.get("smap", {}).get("records", [])}
    gpm_records = {r.get("period"): r for r in datasets.get("gpm", {}).get("records", [])}
    landsat_records = {r.get("period"): r for r in datasets.get("landsat", {}).get("records", [])}
    modis_records = {r.get("period"): r for r in datasets.get("modis", {}).get("records", [])}

    if power_records:
        for pr in power_records:
            period = pr.get("period")
            periods.append(period)

            # Soil moisture
            smap_r = smap_records.get(period, {})
            sm_val = smap_r.get("sm_surface")
            moist_series.append(float(sm_val) if sm_val is not None else None)

            # Rainfall
            gpm_r = gpm_records.get(period, {})
            rain_val = gpm_r.get("rainfall_mm")
            if rain_val is None:
                rain_val = pr.get("PRECTOTCORR_monthly_sum")
            rain_series.append(float(rain_val) if rain_val is not None else None)

            # LST
            ls_r = landsat_records.get(period, {})
            lst_val = ls_r.get("LST_C")
            if lst_val is None:
                lst_val = pr.get("T2M_monthly_mean")
            lst_series.append(float(lst_val) if lst_val is not None else None)

            # NDVI
            ls_ndvi = ls_r.get("NDVI")
            if ls_ndvi is None:
                mod_r = modis_records.get(period, {})
                ls_ndvi = mod_r.get("NDVI")
            ndvi_series.append(float(ls_ndvi) if ls_ndvi is not None else None)
    else:
        # No observations available: report an upstream failure instead of invented values.
        failures = {k: v.get("message") for k, v in datasets.items() if v.get("status") != "ok"}
        raise HTTPException(
            status_code=503,
            detail=f"No satellite or agroclimate observations available right now: {failures or 'no data returned'}"
        )

    return SoilClimateResponse(
        farm_id=farm.id,
        periods=periods,
        moist=moist_series,
        rain=rain_series,
        lst=lst_series,
        ndvi=ndvi_series,
        sources={
            "moist": "NASA SMAP L4 (sm_surface)",
            "rain": "NASA GPM IMERG / NASA POWER (PRECTOTCORR)",
            "lst": "Landsat 8/9 ST_B10 / NASA POWER (T2M)",
            "ndvi": "Landsat 8/9 SR / Terra MODIS (NDVI)"
        },
        caveats="Derived from monthly aggregation of validated Earth observation bands."
    )


@router.post("/api/analyze")
async def analyze_geometry(payload: dict):
    """Ad-hoc GeoJSON / bbox analysis."""
    try:
        from PrithviX_pipeline import run_analysis as pipeline_run
        return await run_in_threadpool(pipeline_run, payload)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))
