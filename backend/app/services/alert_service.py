from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from app.models.farm import Farm
from app.schemas.analysis import AlertItem


def generate_farm_alerts(
    farm: Farm,
    latest_moisture: Optional[float] = None,
    recent_rainfall: Optional[float] = None,
    recent_temp_c: Optional[float] = None,
    latest_ndvi: Optional[float] = None,
    observation_period: Optional[str] = None,
    ee_authenticated: bool = True
) -> List[AlertItem]:
    """Generate categorized, actionable alerts grounded strictly in farm observations."""
    now_str = datetime.now(timezone.utc).strftime("%b %d, %Y, %I:%M %p")
    obs_date = observation_period or now_str
    alerts: List[AlertItem] = []

    # 1. Soil Moisture Alert
    if latest_moisture is not None:
        pct = round(latest_moisture * 100)
        if latest_moisture < 0.20:
            alerts.append(AlertItem(
                s="c",
                t="Water Stress Alert",
                p="All Plots",
                d=obs_date,
                x=f"Volumetric soil moisture is {pct}%, below the critical 20% threshold.",
                a=f"Irrigate {farm.name} within 2 days using {farm.irrigation_method or 'scheduled irrigation'}.",
                source="NASA SMAP L4"
            ))
        elif latest_moisture > 0.38:
            alerts.append(AlertItem(
                s="w",
                t="Excess Soil Moisture",
                p="All Plots",
                d=obs_date,
                x=f"Soil moisture is high at {pct}%, indicating saturation risk.",
                a="Inspect field drainage channels and pause any supplemental watering.",
                source="NASA SMAP L4"
            ))
        else:
            alerts.append(AlertItem(
                s="n",
                t="Soil Moisture Optimal",
                p="All Plots",
                d=obs_date,
                x=f"Soil moisture is steady at {pct}%, within the healthy range.",
                a="Maintain current crop management; no immediate moisture intervention needed.",
                source="NASA SMAP L4"
            ))

    # 2. Vegetation / NDVI Alert
    if latest_ndvi is not None:
        if latest_ndvi < 0.30:
            alerts.append(AlertItem(
                s="w",
                t="Low Vegetation Vigor",
                p="Plot A",
                d=obs_date,
                x=f"Satellite NDVI index is {round(latest_ndvi, 2)}, indicating sparse canopy or post-harvest state.",
                a="Check for nutrient deficiencies or seedling emergence issues.",
                source="Landsat / MODIS"
            ))
        else:
            alerts.append(AlertItem(
                s="n",
                t="Vegetation Canopy Health",
                p="Plot A",
                d=obs_date,
                x=f"NDVI is healthy at {round(latest_ndvi, 2)}, confirming active photosynthetic vigor.",
                a="Continue standard crop protection and fertilization schedule.",
                source="Landsat / MODIS"
            ))

    # 3. Temperature Alert
    if recent_temp_c is not None:
        if recent_temp_c > 35.0:
            alerts.append(AlertItem(
                s="w",
                t="Elevated Surface Temperature",
                p="All",
                d=obs_date,
                x=f"Average surface temperature reached {round(recent_temp_c, 1)} °C.",
                a="Provide shade or mulch if cultivating sensitive horticulture to prevent heat stress.",
                source="NASA POWER / Landsat"
            ))
        elif recent_temp_c < 10.0 and (farm.climate_zone == "trop" or farm.climate_zone == "humid"):
            alerts.append(AlertItem(
                s="w",
                t="Cold Weather Alert",
                p="All",
                d=obs_date,
                x=f"Temperature dropped to {round(recent_temp_c, 1)} °C, unusually low for warm-season crops.",
                a="Protect seedlings against nocturnal chilling injury.",
                source="NASA POWER"
            ))
        else:
            alerts.append(AlertItem(
                s="n",
                t="Temperature Normal",
                p="All",
                d=obs_date,
                x=f"Surface temperature ({round(recent_temp_c, 1)} °C) is within seasonal norms.",
                a="No temperature-related action needed.",
                source="NASA POWER"
            ))

    # 4. Rainfall Alert
    if recent_rainfall is not None:
        if recent_rainfall > 150.0:
            alerts.append(AlertItem(
                s="w",
                t="Heavy Monthly Rainfall",
                p="All",
                d=obs_date,
                x=f"Recorded rainfall accumulated to {round(recent_rainfall, 1)} mm over the period.",
                a="Check fields for ponding and delay pesticide spraying until foliage dries.",
                source="NASA GPM IMERG / POWER"
            ))
        elif recent_rainfall < 10.0:
            alerts.append(AlertItem(
                s="i",
                t="Dry Period / Low Rainfall",
                p="All",
                d=obs_date,
                x=f"Rainfall was low ({round(recent_rainfall, 1)} mm) during the last recorded month.",
                a="Ensure secondary water storage (borewell/tank) is available if dry spell persists.",
                source="NASA GPM IMERG / POWER"
            ))

    # 5. Crop specific planting window info
    crop_name = farm.current_crop or "Seasonal Crop"
    alerts.append(AlertItem(
        s="i",
        t=f"Crop Management: {crop_name}",
        p="Plot A",
        d=obs_date,
        x=f"Target crop '{crop_name}' is registered with primary goal '{farm.primary_goal}'.",
        a="Review crop recommendations and maintain soil moisture according to growth phase.",
        source="PrithviX Farm Profile"
    ))

    # 6. GEE Auth status informational note if unauthenticated
    if not ee_authenticated:
        alerts.append(AlertItem(
            s="i",
            t="Satellite Feed Configuration",
            p="System",
            d=now_str,
            x="Earth Engine requires local user or service account credentials. NASA POWER meteorological feeds are active.",
            a="Run 'earthengine authenticate' or set service account credentials to unlock Landsat and SMAP passes.",
            source="Earth Engine Connector"
        ))

    return alerts
