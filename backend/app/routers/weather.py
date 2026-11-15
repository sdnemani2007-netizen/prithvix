from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.database import get_db
from app.schemas.weather import FarmWeatherResponse
from app.services import farm_service, weather_service

router = APIRouter(prefix="/api/weather", tags=["Weather"])


@router.get("/{farm_id}", response_model=FarmWeatherResponse)
async def get_weather(farm_id: str, db: Session = Depends(get_db)):
    """Retrieve NASA POWER weather analysis for a specific farm."""
    farm = farm_service.get_farm_by_id(db, farm_id)
    if not farm:
        raise HTTPException(status_code=404, detail=f"Farm '{farm_id}' not found.")

    res = await run_in_threadpool(weather_service.get_weather_for_farm, farm)
    return res
