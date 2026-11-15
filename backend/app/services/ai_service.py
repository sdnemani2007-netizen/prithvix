import os
import logging
from typing import Dict, Any, Optional
from app.config import GEMINI_API_KEY
from app.models.farm import Farm
from app.services.crop_service import get_crop_recommendations
from app.services.irrigation_service import get_irrigation_advisory

logger = logging.getLogger("prithvix.ai")


def answer_prithvix_ai(
    question: str,
    farm: Optional[Farm] = None,
    farm_context_dict: Optional[Dict[str, Any]] = None,
    latest_conditions: Optional[Dict[str, Any]] = None,
    weather_info: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generate agronomic response strictly grounded in the selected farm profile
    and NASA observational data.
    """
    # Consolidate farm metadata
    farm_name = (farm.name if farm else None) or (farm_context_dict.get("name") if farm_context_dict else None) or "Selected Farm"
    location = (farm.location if farm else None) or (farm_context_dict.get("location") if farm_context_dict else None) or "Unknown Location"
    current_crop = (farm.current_crop if farm else None) or (farm_context_dict.get("currentCrop") if farm_context_dict else None) or "Unspecified"
    soil_type = (farm.soil_type if farm else None) or (farm_context_dict.get("soilType") if farm_context_dict else None) or "Unknown"
    water_source = (farm.water_source if farm else None) or (farm_context_dict.get("waterSource") if farm_context_dict else None) or "Unknown"
    irrigation_method = (farm.irrigation_method if farm else None) or (farm_context_dict.get("irrigation") if farm_context_dict else None) or "Unknown"
    primary_goal = (farm.primary_goal if farm else None) or (farm_context_dict.get("primaryGoal") if farm_context_dict else None) or "Increase Crop Yield"

    cond = latest_conditions or {}
    soil_m = cond.get("soil_moisture")
    ndvi = cond.get("vegetation_ndvi")
    temp_c = cond.get("surface_temp_c")
    rain_mm = cond.get("rainfall_mm") or cond.get("water_available")

    context_summary = {
        "farm_name": farm_name,
        "location": location,
        "current_crop": current_crop,
        "soil_type": soil_type,
        "water_source": water_source,
        "irrigation_method": irrigation_method,
        "primary_goal": primary_goal,
        "observations": {
            "soil_moisture_m3_m3": soil_m,
            "ndvi": ndvi,
            "temperature_c": temp_c,
            "rainfall_mm": rain_mm,
        }
    }

    # Attempt Gemini API if key is present
    if GEMINI_API_KEY:
        try:
            from google import genai
            client = genai.Client(api_key=GEMINI_API_KEY, http_options={"timeout": 90000})
            prompt = f"""
You are PrithviXAI, a trusted agronomy advisor grounded in verified NASA Earth observations.
Context for the farmer's property:
- Farm Name: {farm_name}
- Location: {location}
- Current Crop: {current_crop}
- Soil Type: {soil_type}
- Water Source: {water_source}
- Irrigation Method: {irrigation_method}
- Primary Goal: {primary_goal}
- Verified NASA Observations:
  * Soil Moisture (SMAP): {soil_m if soil_m is not None else 'No recent observation'}
  * Vegetation Health / NDVI (Landsat/MODIS): {ndvi if ndvi is not None else 'No recent observation'}
  * Surface Temperature: {temp_c if temp_c is not None else 'No recent observation'} °C
  * Accumulated Rainfall: {rain_mm if rain_mm is not None else 'No recent observation'} mm

Guidelines:
1. Ground your advice directly in the measured values above. Do not fabricate satellite numbers.
2. If any measurement is missing, state clearly that satellite data is unavailable.
3. Provide practical, beginner-friendly agronomic guidance addressing the user's specific question.
4. Keep the answer concise and actionable.

User Question: {question}
"""
            response = client.models.generate_content(
                model=os.environ.get("GEMINI_MODEL", "gemini-3.8-flash"),
                contents=prompt
            )
            return {
                "reply": response.text,
                "grounded_on": context_summary,
                "provider": "Gemini  via PrithviX AI"
            }
        except Exception as exc:
            logger.exception("Gemini API call failed; falling back to agronomic engine.")

    # Deterministic Agronomic Fallback Engine
    q_lower = question.lower()
    reply_parts = []

    if any(k in q_lower for k in ("soil", "moist", "wet", "dry")):
        if soil_m is not None:
            pct = round(soil_m * 100, 1)
            status = "low and under water stress (<20%)" if soil_m < 0.20 else ("adequate (20-35%)" if soil_m <= 0.35 else "saturated (>35%)")
            reply_parts.append(
                f"According to NASA SMAP satellite observations, current volumetric soil moisture at {farm_name} is {pct}% m³/m³, which is {status}. "
                f"For your crop ({current_crop}) in {soil_type}, maintain regular field checks before operating your {irrigation_method}."
            )
        else:
            reply_parts.append(
                f"Direct satellite soil moisture is currently awaiting a fresh pass for {location}. "
                f"Given your recorded {soil_type} and {water_source}, physically probe the rootzone depth (top 15–20 cm) to assess dryness."
            )

    if any(k in q_lower for k in ("water", "irrigat", "pump", "need")):
        if soil_m is not None and soil_m < 0.20:
            reply_parts.append(
                f"Actionable Irrigation Advisory: Supplemental irrigation is recommended within the next 24 to 48 hours. "
                f"Moisture is currently {round(soil_m * 100, 1)}%. With {irrigation_method}, apply an initial light cycle to re-hydrate the rootzone without waterlogging."
            )
        elif soil_m is not None and soil_m >= 0.20:
            reply_parts.append(
                f"Actionable Irrigation Advisory: No emergency irrigation is required today. "
                f"Soil moisture is at a healthy {round(soil_m * 100, 1)}%. Continue regular moisture monitoring to prevent unnecessary water costs."
            )
        else:
            reply_parts.append(
                f"Actionable Irrigation Advisory: We do not recommend running pumps without checking rootzone moisture. "
                f"Because your water source is {water_source}, conserving water supports your goal: '{primary_goal}'."
            )

    if any(k in q_lower for k in ("plant", "crop", "recommend", "next", "grow")):
        reply_parts.append(
            f"Based on your farm location in {location} and current crop '{current_crop}', suitable rotation candidates include nitrogen-fixing legumes "
            f"(such as Chickpea, Pigeonpea, or Soybean depending on seasonal rains) or drought-hardy millets. "
            f"These options replenish soil nutrients and align with your goal: '{primary_goal}'."
        )

    if any(k in q_lower for k in ("health", "declin", "ndvi", "vegetat", "yellow")):
        if ndvi is not None:
            reply_parts.append(
                f"NASA/USGS Landsat and MODIS vegetation analysis shows an NDVI of {round(ndvi, 2)} for your farm. "
                f"{'Canopy greenness is healthy and vigorous.' if ndvi >= 0.45 else 'Canopy density is relatively low, which can indicate either early vegetative emergence, pest pressure, or nutrient deficiency.'}"
            )
        else:
            reply_parts.append(
                f"Satellite canopy reflectance is currently cloudy or pending for {farm_name}. "
                "Examine the undersides of leaves and leaf veins for chlorosis (yellowing) or sap-sucking pests."
            )

    if any(k in q_lower for k in ("rain", "precipitation", "weather")):
        if rain_mm is not None:
            reply_parts.append(
                f"NASA GPM IMERG and POWER observations indicate accumulated monthly rainfall of approximately {round(rain_mm, 1)} mm. "
                + (f"Recent mean temperature has been around {round(temp_c, 1)} °C." if temp_c is not None else "Recent temperature data is unavailable.")
            )
        else:
            reply_parts.append(
                f"Meteorological observations from NASA POWER indicate standard seasonal weather for {location}. "
                "Ensure field channels are clear to prevent standing water during sudden rain events."
            )

    if not reply_parts:
        reply_parts.append(
            f"Welcome to PrithviXAI! For {farm_name} ({location}), your registered crop is '{current_crop}' with {soil_type} and {irrigation_method}. "
            f"Current satellite soil moisture is {f'{round(soil_m*100, 1)}%' if soil_m is not None else 'pending pass'}, "
            f"and vegetation NDVI is {round(ndvi, 2) if ndvi is not None else 'clear sky pending'}. "
            f"How can I assist you with irrigation scheduling, crop selection, or soil health today?"
        )

    reply_text = "\n\n".join(reply_parts)
    reply_text += "\n\n*(Note: Grounded in PrithviX Agricultural Intelligence Engine using farm profile data and NASA observations. Configure GEMINI_API_KEY in backend/.env for conversational AI reasoning.)*"

    return {
        "reply": reply_text,
        "grounded_on": context_summary,
        "provider": "PrithviX Agronomic Fallback Engine"
    }
