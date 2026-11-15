import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.database import get_db
from app.schemas.analysis import CropRecommendationResponse, CropRotationResponse
from app.services import farm_service, crop_service, earth_engine
from app.utils.geo import parse_boundary_to_geojson

router = APIRouter(prefix="/api/crops", tags=["Crops"])


@router.get("/recommendations/{farm_id}", response_model=CropRecommendationResponse)
async def get_crop_recommendations(farm_id: str, db: Session = Depends(get_db)):
    """Retrieve grounded crop suitability recommendations for a farm."""
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

    return crop_service.get_crop_recommendations(
        farm=farm,
        latest_moisture=soil_m,
        recent_rainfall=rain_val,
        recent_temp_c=temp_c
    )


@router.get("/rotation/{farm_id}", response_model=CropRotationResponse)
def get_crop_rotation(farm_id: str, db: Session = Depends(get_db)):
    """Retrieve agronomic crop rotation cycles for a farm."""
    farm = farm_service.get_farm_by_id(db, farm_id)
    if not farm:
        raise HTTPException(status_code=404, detail=f"Farm '{farm_id}' not found.")

    return crop_service.get_crop_rotation_plans(farm)
