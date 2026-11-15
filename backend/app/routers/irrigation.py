import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.database import get_db
from app.schemas.analysis import IrrigationAdvisoryResponse
from app.services import farm_service, irrigation_service, earth_engine
from app.utils.geo import parse_boundary_to_geojson

router = APIRouter(prefix="/api/irrigation", tags=["Irrigation"])


@router.get("/{farm_id}", response_model=IrrigationAdvisoryResponse)
async def get_irrigation(farm_id: str, db: Session = Depends(get_db)):
    """Retrieve farm-specific irrigation advisory based on soil moisture and recent rain."""
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
        centroid_lon=farm.longitude,
        datasets=["smap", "nasa_power"]
    )

    summary = analysis.get("summary", {})
    soil_m = summary.get("latest_smap_surface_soil_moisture_m3_m3")
    rain_val = summary.get("latest_nasa_power_rainfall_mm")
    temp_c = summary.get("latest_nasa_power_temp_c")
    period = summary.get("latest_smap_surface_soil_moisture_m3_m3_period") or summary.get("latest_nasa_power_period")

    return irrigation_service.get_irrigation_advisory(
        farm=farm,
        latest_soil_moisture=soil_m,
        recent_rainfall_mm=rain_val,
        recent_temp_c=temp_c,
        observation_period=period
    )
