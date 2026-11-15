import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.database import get_db
from app.schemas.analysis import AlertItem
from app.services import farm_service, alert_service, earth_engine
from app.utils.geo import parse_boundary_to_geojson

router = APIRouter(prefix="/api/alerts", tags=["Alerts"])


@router.get("/{farm_id}", response_model=List[AlertItem])
async def get_alerts(farm_id: str, db: Session = Depends(get_db)):
    """Retrieve actionable alerts and advice for a farm."""
    farm = farm_service.get_farm_by_id(db, farm_id)
    if not farm:
        raise HTTPException(status_code=404, detail=f"Farm '{farm_id}' not found.")

    geom = parse_boundary_to_geojson(
        json.loads(farm.boundary_geojson) if farm.boundary_geojson else None,
        farm.latitude,
        farm.longitude
    )

    analysis = await run_in_threadpool(
        earth_engine.run_farm_analysis,
        geometry_geojson=geom,
        location_id=farm.id,
        location_name=farm.name,
        centroid_lat=farm.latitude,
        centroid_lon=farm.longitude
    )

    summary = analysis.get("summary", {})
    soil_m = summary.get("latest_smap_surface_soil_moisture_m3_m3")
    rain_val = summary.get("gpm_total_rainfall_mm_over_period") or summary.get("latest_nasa_power_rainfall_mm")
    temp_c = summary.get("latest_landsat_land_surface_temp_c") or summary.get("latest_nasa_power_temp_c")
    ndvi = summary.get("latest_landsat_ndvi") or summary.get("latest_modis_ndvi")
    period = summary.get("latest_smap_surface_soil_moisture_m3_m3_period") or summary.get("latest_nasa_power_period")

    ee_ready = bool(analysis.get("integration", {}).get("earth_engine_status", {}).get("initialized"))

    return alert_service.generate_farm_alerts(
        farm=farm,
        latest_moisture=soil_m,
        recent_rainfall=rain_val,
        recent_temp_c=temp_c,
        latest_ndvi=ndvi,
        observation_period=period,
        ee_authenticated=ee_ready
    )
