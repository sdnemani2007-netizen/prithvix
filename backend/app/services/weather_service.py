from datetime import datetime, timezone
import pandas as pd
from typing import Dict, Any, Optional
from app.models.farm import Farm
from app.services.earth_engine import extract_nasa_power


def get_weather_for_farm(farm: Farm, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve NASA POWER agroclimatology for the farm."""
    if not start_date:
        # Default last 12 months
        start_date = (pd.Timestamp.now(tz="UTC") - pd.DateOffset(months=12)).replace(day=1).strftime("%Y-%m-%d")
    if not end_date:
        end_date = pd.Timestamp.now(tz="UTC").normalize().replace(day=1).strftime("%Y-%m-%d")

    power_result = extract_nasa_power(
        centroid_lon=farm.longitude,
        centroid_lat=farm.latitude,
        start_date=start_date,
        end_date=end_date
    )

    records = power_result.get("records", [])
    latest_monthly = records[-1] if records else None

    return {
        "farm_id": farm.id,
        "location": farm.location,
        "latitude": farm.latitude,
        "longitude": farm.longitude,
        "source": "NASA POWER Daily Agroclimatology (Centroid sampling)",
        "latest_monthly": latest_monthly,
        "recent_trend": records[-6:] if records else [],
        "caveats": (
            "NASA POWER is a gridded meteorological model estimate (1/2° × 5/8° resolution) "
            "sampled at farm centroid, not an on-farm physical weather station."
        )
    }
