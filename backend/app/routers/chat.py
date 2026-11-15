import json
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.database import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.services import farm_service, ai_service, earth_engine
from app.utils.geo import parse_boundary_to_geojson

router = APIRouter(tags=["AI Assistant"])


@router.post("/api/chat", response_model=ChatResponse)
@router.post("/chat", response_model=ChatResponse)
async def chat_with_prithvix_ai(request: ChatRequest, db: Session = Depends(get_db)):
    """
    PrithviXAI conversational interface grounded in farm profile and NASA observations.
    """
    farm = None
    if request.farm_id:
        farm = farm_service.get_farm_by_id(db, request.farm_id)

    farm_dict = request.farm.dict() if request.farm else None

    # Load observational data if farm available
    latest_conditions = {}
    if farm:
        try:
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
            latest_conditions = {
                "soil_moisture": summary.get("latest_smap_surface_soil_moisture_m3_m3"),
                "vegetation_ndvi": summary.get("latest_landsat_ndvi") or summary.get("latest_modis_ndvi"),
                "surface_temp_c": summary.get("latest_landsat_land_surface_temp_c") or summary.get("latest_nasa_power_temp_c"),
                "rainfall_mm": summary.get("gpm_total_rainfall_mm_over_period") or summary.get("latest_nasa_power_rainfall_mm")
            }
        except Exception:
            # Satellite lookup failed: the assistant will state that observations are unavailable.
            latest_conditions = {}

    res = await run_in_threadpool(
        ai_service.answer_prithvix_ai,
        question=request.message,
        farm=farm,
        farm_context_dict=farm_dict,
        latest_conditions=latest_conditions
    )

    return ChatResponse(
        reply=res["reply"],
        grounded_on=res.get("grounded_on"),
        provider=res.get("provider")
    )
