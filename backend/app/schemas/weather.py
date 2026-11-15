from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class WeatherRecord(BaseModel):
    period: str
    daily_record_count: Optional[int] = None
    precipitation_monthly_sum_mm: Optional[float] = None
    temperature_monthly_mean_c: Optional[float] = None
    relative_humidity_monthly_mean_pct: Optional[float] = None
    solar_radiation_monthly_mean_mj_m2: Optional[float] = None


class FarmWeatherResponse(BaseModel):
    farm_id: str
    location: str
    latitude: float
    longitude: float
    source: str = "NASA POWER Daily Agroclimatology"
    latest_monthly: Optional[Dict[str, Any]] = None
    recent_trend: List[Dict[str, Any]] = Field(default_factory=list)
    caveats: str
