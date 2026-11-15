from typing import List, Dict, Any, Optional
from app.models.farm import Farm
from app.schemas.analysis import CropRecommendation, CropRecommendationResponse, RotationPlan, CropRotationResponse

# Agronomic knowledge base indexed by climate zone and crop attributes
ZONE_CROPS = {
    "trop": [
        {
            "name": "Rice / Paddy",
            "base_score": 82,
            "water_need": "High",
            "optimal_temp_c": (22, 34),
            "optimal_moist": (0.28, 0.45),
            "suitable_soils": ["Clay Soil", "Alluvial Soil", "Black Cotton Soil (Vertisol)"],
            "reason": "Tropical warmth and monsoon moisture strongly support wetland or transplanted paddy cultivation.",
            "limitations": "Susceptible to water stress if irrigation supply or rainfall drops below 150 mm/month during tillering."
        },
        {
            "name": "Groundnut",
            "base_score": 75,
            "water_need": "Medium",
            "optimal_temp_c": (24, 32),
            "optimal_moist": (0.18, 0.30),
            "suitable_soils": ["Red Soil", "Sandy Soil", "Loamy Soil"],
            "reason": "Legume requiring well-drained soil; fixes atmospheric nitrogen and handles intermittent rainfall.",
            "limitations": "Poor yield in waterlogged or heavy compacted clay soils."
        },
        {
            "name": "Millets / Sorghum",
            "base_score": 78,
            "water_need": "Low",
            "optimal_temp_c": (25, 36),
            "optimal_moist": (0.14, 0.25),
            "suitable_soils": ["Red Soil", "Sandy Soil", "Loamy Soil", "Black Cotton Soil (Vertisol)"],
            "reason": "Exceptional drought resilience and low nutrient requirement, thriving under dry spell conditions.",
            "limitations": "Lower market price ceiling compared to commercial oilseeds or cotton."
        },
        {
            "name": "Cotton",
            "base_score": 68,
            "water_need": "Medium",
            "optimal_temp_c": (22, 35),
            "optimal_moist": (0.20, 0.32),
            "suitable_soils": ["Black Cotton Soil (Vertisol)", "Alluvial Soil"],
            "reason": "Deep taproot system thrives in high water-holding capacity vertisols with warm sunny weather.",
            "limitations": "Excess late-season rain during boll opening can cause rot and lower lint quality."
        },
        {
            "name": "Pulses / Pigeonpea",
            "base_score": 74,
            "water_need": "Low",
            "optimal_temp_c": (20, 32),
            "optimal_moist": (0.15, 0.28),
            "suitable_soils": ["Black Cotton Soil (Vertisol)", "Loamy Soil", "Red Soil"],
            "reason": "Nitrogen-fixing pulse with deep taproots suitable for intercropping and low-input fertility enhancement.",
            "limitations": "Vulnerable to pod borer infestation and waterlogging during early germination."
        }
    ],
    "humid": [
        {
            "name": "Rice / Paddy",
            "base_score": 80,
            "water_need": "High",
            "optimal_temp_c": (20, 32),
            "optimal_moist": (0.28, 0.42),
            "suitable_soils": ["Alluvial Soil", "Clay Soil", "Silty Soil"],
            "reason": "High humidity and reliable monsoon/summer rainfall provide favorable moisture conditions.",
            "limitations": "Risk of fungal blast during extended cloudy/high-humidity periods."
        },
        {
            "name": "Soybean",
            "base_score": 76,
            "water_need": "Medium",
            "optimal_temp_c": (20, 30),
            "optimal_moist": (0.22, 0.35),
            "suitable_soils": ["Loamy Soil", "Black Cotton Soil (Vertisol)", "Alluvial Soil"],
            "reason": "Excellent summer pulse fitting between winter cereals, enriching soil organic nitrogen.",
            "limitations": "Moisture stress during pod filling significantly reduces test weight."
        },
        {
            "name": "Wheat",
            "base_score": 72,
            "water_need": "Medium",
            "optimal_temp_c": (12, 24),
            "optimal_moist": (0.20, 0.32),
            "suitable_soils": ["Alluvial Soil", "Loamy Soil", "Clay Soil"],
            "reason": "Prime winter rabi crop benefiting from cool vegetative stages and dry harvest weather.",
            "limitations": "Terminal heat during grain-filling (temperatures > 30 °C) can cause premature senescence."
        },
        {
            "name": "Maize",
            "base_score": 70,
            "water_need": "Medium",
            "optimal_temp_c": (18, 30),
            "optimal_moist": (0.22, 0.34),
            "suitable_soils": ["Loamy Soil", "Alluvial Soil"],
            "reason": "High photosynthetic efficiency (C4) yielding strong biomass when moisture is adequate.",
            "limitations": "High nitrogen demand; sensitive to drought during silking."
        }
    ],
    "med": [
        {
            "name": "Wheat",
            "base_score": 78,
            "water_need": "Medium",
            "optimal_temp_c": (14, 25),
            "optimal_moist": (0.18, 0.30),
            "suitable_soils": ["Loamy Soil", "Clay Soil", "Alluvial Soil"],
            "reason": "Well adapted to winter rainfall patterns and sunny spring ripening conditions.",
            "limitations": "Yield drops without supplemental spring irrigation if winter rains terminate early."
        },
        {
            "name": "Barley",
            "base_score": 74,
            "water_need": "Low",
            "optimal_temp_c": (12, 22),
            "optimal_moist": (0.15, 0.26),
            "suitable_soils": ["Loamy Soil", "Sandy Soil", "Chalky Soil"],
            "reason": "High drought and mild salinity tolerance with shorter season than bread wheat.",
            "limitations": "Lodging risk under excessive nitrogen application."
        },
        {
            "name": "Chickpea",
            "base_score": 71,
            "water_need": "Low",
            "optimal_temp_c": (15, 28),
            "optimal_moist": (0.15, 0.25),
            "suitable_soils": ["Loamy Soil", "Red Soil", "Black Cotton Soil (Vertisol)"],
            "reason": "Deep-rooting legume that utilizes residual soil moisture after winter.",
            "limitations": "Highly susceptible to Ascochyta blight in wet springs."
        },
        {
            "name": "Vegetables / Tomatoes",
            "base_score": 65,
            "water_need": "High",
            "optimal_temp_c": (18, 30),
            "optimal_moist": (0.25, 0.38),
            "suitable_soils": ["Loamy Soil", "Alluvial Soil", "Sandy Soil"],
            "reason": "High-value horticulture that yields exceptionally well with managed drip irrigation.",
            "limitations": "Requires dedicated, reliable drip infrastructure; high blossom-end rot risk if water fluctuates."
        }
    ],
    "temp": [
        {
            "name": "Wheat",
            "base_score": 77,
            "water_need": "Medium",
            "optimal_temp_c": (10, 22),
            "optimal_moist": (0.20, 0.32),
            "suitable_soils": ["Loamy Soil", "Clay Soil", "Silty Soil"],
            "reason": "Ideal thermal regime for winter/spring wheat with steady grain filling.",
            "limitations": "Susceptible to fungal rust and Fusarium head blight in damp harvests."
        },
        {
            "name": "Canola / Rapeseed",
            "base_score": 73,
            "water_need": "Medium",
            "optimal_temp_c": (12, 22),
            "optimal_moist": (0.20, 0.30),
            "suitable_soils": ["Loamy Soil", "Clay Soil"],
            "reason": "Excellent break crop for cereal rotations; enhances soil structure.",
            "limitations": "High sulfur and nitrogen needs; vulnerable to early flea beetle attack."
        },
        {
            "name": "Field Peas / Legumes",
            "base_score": 69,
            "water_need": "Low",
            "optimal_temp_c": (10, 20),
            "optimal_moist": (0.18, 0.28),
            "suitable_soils": ["Loamy Soil", "Silty Soil", "Sandy Soil"],
            "reason": "Cool-season nitrogen fixer reducing fertilizer requirements for subsequent crops.",
            "limitations": "Sensitive to heat stress during flowering (>26 °C causes flower abortion)."
        }
    ]
}


def get_crop_recommendations(
    farm: Farm,
    latest_moisture: Optional[float] = None,
    recent_rainfall: Optional[float] = None,
    recent_temp_c: Optional[float] = None
) -> CropRecommendationResponse:
    """
    Generate transparent, evidence-based crop recommendations based on
    satellite observations and farm profile.
    """
    zone = farm.climate_zone or "trop"
    candidate_crops = ZONE_CROPS.get(zone, ZONE_CROPS["trop"])

    recommendations: List[CropRecommendation] = []
    observations_found = []

    if latest_moisture is not None:
        observations_found.append(f"Satellite soil moisture: {round(latest_moisture * 100, 1)}% volumetric (SMAP)")
    if recent_rainfall is not None:
        observations_found.append(f"Recent monthly rainfall: {round(recent_rainfall, 1)} mm (GPM / POWER)")
    if recent_temp_c is not None:
        observations_found.append(f"Observed temperature: {round(recent_temp_c, 1)} °C (POWER / Landsat)")

    for c in candidate_crops:
        score = c["base_score"]
        supporting = list(observations_found)
        limits = [c["limitations"]]

        # Soil type match
        if farm.soil_type and farm.soil_type != "Unknown":
            if farm.soil_type in c["suitable_soils"]:
                score += 8
                supporting.append(f"Soil '{farm.soil_type}' matches ideal physical characteristics for {c['name']}.")
            else:
                score -= 6
                limits.append(f"Soil '{farm.soil_type}' is sub-optimal; requires soil conditioning or drainage management.")

        # Soil moisture adjustment
        if latest_moisture is not None:
            min_m, max_m = c["optimal_moist"]
            if min_m <= latest_moisture <= max_m:
                score += 6
                supporting.append(f"Current soil moisture ({round(latest_moisture * 100)}%) falls directly within the ideal vegetative range ({int(min_m*100)}–{int(max_m*100)}%).")
            elif latest_moisture < min_m:
                if c["water_need"] == "Low":
                    score += 4
                    supporting.append(f"Dry soil conditions ({round(latest_moisture * 100)}%) favor drought-tolerant {c['name']}.")
                else:
                    score -= 10
                    limits.append(f"Current soil moisture ({round(latest_moisture * 100)}%) is below optimal ({int(min_m*100)}%); supplemental irrigation will be essential.")

        # Temperature adjustment
        if recent_temp_c is not None:
            min_t, max_t = c["optimal_temp_c"]
            if min_t <= recent_temp_c <= max_t:
                score += 5
                supporting.append(f"Observed temperature ({round(recent_temp_c, 1)} °C) aligns with the optimal development bracket ({min_t}–{max_t} °C).")
            elif recent_temp_c > max_t:
                score -= 8
                limits.append(f"Temperature ({round(recent_temp_c, 1)} °C) exceeds optimum ({max_t} °C), increasing evaporation and flower shedding risk.")

        # Goal adjustment
        if farm.primary_goal == "Reduce Water Consumption" and c["water_need"] == "Low":
            score += 10
            supporting.append("Matches primary goal: low water requirement.")
        elif farm.primary_goal == "Improve Soil Health" and ("Legume" in c["reason"] or "Pulse" in c["reason"]):
            score += 10
            supporting.append("Matches primary goal: biological nitrogen fixation improves soil fertility.")

        score = max(35, min(95, score))
        confidence = "High" if len(observations_found) >= 2 else "Moderate"

        recommendations.append(CropRecommendation(
            n=c["name"],
            sc=score,
            w=c["water_need"],
            why=c["reason"],
            supporting_observations=supporting,
            limitations=limits,
            confidence=confidence
        ))

    recommendations.sort(key=lambda x: x.sc, reverse=True)

    summary_text = (
        f"Evaluated {len(recommendations)} candidate crops for {farm.name} (Zone: {zone}). "
        f"Grounded in {len(observations_found)} verified observational feeds and farmer profile goals."
    )

    return CropRecommendationResponse(
        farm_id=farm.id,
        climate_zone=zone,
        current_crop=farm.current_crop,
        soil_type=farm.soil_type,
        recommendations=recommendations,
        agronomic_summary=summary_text
    )


def get_crop_rotation_plans(farm: Farm) -> CropRotationResponse:
    """
    Generate balanced crop rotation schedules considering current crop,
    legume-cereal alternation, pest cycle disruption, and soil fertility.
    """
    zone = farm.climate_zone or "trop"
    current = farm.current_crop or "Cereal"

    if zone == "trop":
        plans = {
            "Balanced Agro-Ecological": RotationPlan(
                A=["Rice / Paddy", "Chickpea / Lentil", "Maize", "Groundnut"],
                B=["Maize", "Soybean", "Millets / Sorghum", "Pigeonpea / Pulses"],
                note="Alternates high-nitrogen depleting cereals with nitrogen-fixing legumes, reducing synthetic fertilizer requirements by up to 25%."
            ),
            "Water-Conservation Plan": RotationPlan(
                A=["Groundnut", "Millets / Sorghum", "Pulses", "Sorghum"],
                B=["Millets", "Chickpea", "Sorghum", "Cowpea"],
                note="Prioritizes drought-hardy legumes and C4 millets; suitable during deficit rainfall seasons."
            ),
            "Commercial Yield Maximizer": RotationPlan(
                A=["Cotton", "Chickpea", "Rice / Paddy", "Groundnut"],
                B=["Rice / Paddy", "Wheat", "Cotton", "Soybean"],
                note="Maximizes cash crop yield while maintaining legume breaks to reduce root-knot nematode build-up."
            )
        }
    elif zone == "humid":
        plans = {
            "Balanced Agro-Ecological": RotationPlan(
                A=["Rice / Paddy", "Wheat", "Soybean", "Barley"],
                B=["Soybean", "Wheat", "Rice / Paddy", "Mustard"],
                note="Classic rice-wheat-pulse cycle. Summer soybean fixes nitrogen for subsequent high-yield winter wheat."
            ),
            "Cereal-Legume Diversity": RotationPlan(
                A=["Maize", "Chickpea", "Rice / Paddy", "Lentil"],
                B=["Soybean", "Wheat", "Maize", "Mustard"],
                note="Diversified rotation breaking monoculture pest reservoirs and improving soil water retention."
            )
        }
    elif zone == "med":
        plans = {
            "Balanced Agro-Ecological": RotationPlan(
                A=["Wheat", "Chickpea", "Barley", "Tomato"],
                B=["Barley", "Chickpea", "Wheat", "Sunflower"],
                note="Winter cereal followed by spring chickpea break. Conserves moisture and avoids weed seed carry-over."
            ),
            "Dryland Soil-Restoration": RotationPlan(
                A=["Barley", "Lentil", "Wheat", "Fallow / Cover Crop"],
                B=["Wheat", "Field Peas", "Barley", "Chickpea"],
                note="Restores soil organic carbon with minimal water demand."
            )
        }
    else:  # temp
        plans = {
            "Balanced Agro-Ecological": RotationPlan(
                A=["Wheat", "Field Peas", "Barley", "Canola"],
                B=["Barley", "Canola", "Wheat", "Field Peas"],
                note="Standard 4-year cycle. Deep-rooted canola breaks cereal disease cycles; peas provide residual nitrogen."
            ),
            "Soil Health Focus": RotationPlan(
                A=["Oats", "Clover / Legume Cover", "Wheat", "Canola"],
                B=["Wheat", "Field Peas", "Barley", "Cover Crop"],
                note="Focuses on building microbial biomass and long-term soil structure."
            )
        }

    return CropRotationResponse(
        farm_id=farm.id,
        plans=plans,
        agronomic_advice=(
            f"Rotation plans customized for {farm.name} (Zone: {zone}, Current: {current}). "
            "Never follow cereals with the same cereal family across consecutive seasons without a legume or oilseed break."
        )
    )
