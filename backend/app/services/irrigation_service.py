from typing import Optional, Dict, Any, List
from app.models.farm import Farm
from app.schemas.analysis import IrrigationAdvisoryResponse


def get_irrigation_advisory(
    farm: Farm,
    latest_soil_moisture: Optional[float] = None,
    recent_rainfall_mm: Optional[float] = None,
    recent_temp_c: Optional[float] = None,
    observation_period: Optional[str] = None
) -> IrrigationAdvisoryResponse:
    """
    Generate actionable irrigation advisory based on actual satellite soil moisture,
    recent rainfall, and atmospheric evaporative demand.
    """
    data_sources = []
    if latest_soil_moisture is not None:
        data_sources.append("NASA SMAP L4 (9 km model-assimilated soil moisture)")
    if recent_rainfall_mm is not None:
        data_sources.append("NASA GPM IMERG / NASA POWER Precipitation")
    if recent_temp_c is not None:
        data_sources.append("NASA POWER / Landsat Thermal observations")

    if latest_soil_moisture is None:
        status = "Unknown / Awaiting Satellite Pass"
        advisory = "Monitor soil moisture manually before scheduling irrigation."
        explanation = (
            "No recent satellite soil moisture observation is available for this farm geometry. "
            "Inspect physical rootzone dampness before operating irrigation equipment."
        )
    elif latest_soil_moisture < 0.20:
        status = "Low / Water Stress (<20% volumetric)"
        if recent_rainfall_mm is not None and recent_rainfall_mm > 30.0:
            advisory = "Hold irrigation temporarily; recent rainfall will infiltrate the rootzone."
            explanation = (
                f"Volumetric soil moisture is low ({round(latest_soil_moisture * 100, 1)}%), but recent "
                f"accumulated rainfall ({round(recent_rainfall_mm, 1)} mm) will replenish the profile. "
                "Verify field infiltration before running pumps."
            )
        else:
            method = farm.irrigation_method if farm.irrigation_method and farm.irrigation_method != "Unknown" else "drip / furrow"
            advisory = f"Apply irrigation within 24 to 48 hours via {method}."
            explanation = (
                f"Soil moisture has dropped to {round(latest_soil_moisture * 100, 1)}% m³/m³, indicating "
                f"depleted rootzone reserves below the standard 20% stress threshold for {farm.current_crop or 'field crops'}."
            )
    elif latest_soil_moisture <= 0.35:
        status = "Adequate / Optimal (20% – 35% volumetric)"
        advisory = "Maintain regular maintenance schedule; no immediate supplemental irrigation needed."
        explanation = (
            f"Available soil moisture is at {round(latest_soil_moisture * 100, 1)}% m³/m³, which maintains "
            "healthy root water potential and supports normal crop transpiration."
        )
    else:
        status = "High / Saturated (>35% volumetric)"
        advisory = "Suspend all irrigation and ensure field drainage channels are clear."
        explanation = (
            f"Soil moisture is high at {round(latest_soil_moisture * 100, 1)}% m³/m³. Further watering risks "
            "hypoxia (root suffocation), nutrient leaching, and root rot diseases."
        )

    # Weather demand context
    if recent_temp_c is not None and recent_temp_c > 32.0:
        explanation += f" High temperatures ({round(recent_temp_c, 1)} °C) accelerate evapotranspiration rates; monitor moisture drawdown closely."

    limitations = (
        "Calculations are based on 9 km regional satellite assimilation (SMAP) and centroid weather grids. "
        "Specific volumetric depth (e.g. mm of water per ha) requires in-situ sensor depth, exact crop vegetative stage, "
        "and soil field capacity/wilting point lab tests. PrithviX does not fabricate volumetric delivery gallons without field sensors."
    )

    return IrrigationAdvisoryResponse(
        farm_id=farm.id,
        current_soil_moisture=latest_soil_moisture,
        soil_moisture_status=status,
        recent_rainfall_mm=recent_rainfall_mm,
        recent_temp_c=recent_temp_c,
        advisory=advisory,
        explanation=explanation,
        observation_date=observation_period,
        data_sources=data_sources,
        limitations=limitations
    )
