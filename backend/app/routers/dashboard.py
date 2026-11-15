import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.farm import Farm
from app.models.observation import SatelliteCache
from app.schemas.analysis import DashboardResponse, DashboardConditions, PlotCondition
from app.services import farm_service, earth_engine, alert_service
from app.utils.geo import parse_boundary_to_geojson

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/{farm_id}", response_model=DashboardResponse)
def get_dashboard(farm_id: str, db: Session = Depends(get_db)):
    """Retrieve synthesized dashboard metrics and condition gauges for a farm."""
    farm = farm_service.get_farm_by_id(db, farm_id)
    if not farm:
        raise HTTPException(status_code=404, detail=f"Farm '{farm_id}' not found.")

    # 1. Retrieve or run analysis
    geom = parse_boundary_to_geojson(
        json.loads(farm.boundary_geojson) if farm.boundary_geojson else None,
        farm.latitude,
        farm.longitude
    )

    analysis = earth_engine.run_farm_analysis(
        geometry_geojson=geom,
        location_id=farm.id,
        location_name=farm.name,
        centroid_lat=farm.latitude,
        centroid_lon=farm.longitude
    )

    summary = analysis.get("summary", {})
    datasets = analysis.get("datasets", {})

    # Extract primary metrics
    soil_m = summary.get("latest_smap_surface_soil_moisture_m3_m3")
    ndvi = summary.get("latest_landsat_ndvi") or summary.get("latest_modis_ndvi")
    temp_c = summary.get("latest_landsat_land_surface_temp_c") or summary.get("latest_nasa_power_temp_c")
    rain_val = summary.get("gpm_total_rainfall_mm_over_period") or summary.get("latest_nasa_power_rainfall_mm")

    # Dates and source attribution
    obs_dates = {}
    sources = {}

    if "latest_smap_surface_soil_moisture_m3_m3_period" in summary:
        obs_dates["SMAP"] = summary["latest_smap_surface_soil_moisture_m3_m3_period"]
        sources["SMAP"] = "NASA SMAP L4 (9 km)"
    if "latest_landsat_ndvi_period" in summary:
        obs_dates["Landsat"] = summary["latest_landsat_ndvi_period"]
        sources["Landsat"] = "Landsat 8/9 C2 T1 (30 m)"
    elif "latest_modis_ndvi_period" in summary:
        obs_dates["MODIS"] = summary["latest_modis_ndvi_period"]
        sources["MODIS"] = "Terra MODIS MOD13Q1 (250 m)"
    if "latest_nasa_power_period" in summary:
        obs_dates["NASA POWER"] = summary["latest_nasa_power_period"]
        sources["NASA POWER"] = "NASA POWER Daily (Centroid)"

    water_status = "Adequate"
    if soil_m is not None:
        if soil_m < 0.20:
            water_status = "Low / Water Stress"
        elif soil_m > 0.35:
            water_status = "High / Saturated"
    elif rain_val is not None:
        water_status = "Adequate" if rain_val > 30 else "Low"

    conditions = DashboardConditions(
        soil_moisture=soil_m,
        soil_moisture_str=f"{round(soil_m * 100)}%" if soil_m is not None else "--",
        vegetation_ndvi=round(ndvi, 2) if ndvi is not None else None,
        vegetation_ndvi_str=f"NDVI {round(ndvi, 2)}" if ndvi is not None else "--",
        water_available=soil_m if soil_m is not None else (rain_val / 100.0 if rain_val else None),
        water_available_status=water_status,
        surface_temp_c=round(temp_c, 1) if temp_c is not None else None,
        surface_temp_str=f"{round(temp_c, 1)} °C" if temp_c is not None else "--",
        observation_dates=obs_dates,
        sources=sources
    )

    # Single whole-farm record built only from real observations.
    # Missing satellite values stay None (never replaced with invented numbers).
    if soil_m is None:
        plot_status = "No recent satellite observation"
    else:
        plot_status = "Water stress" if soil_m < 0.20 else "Healthy"

    plots = [
        PlotCondition(
            id="A",
            name=farm.name or "Farm",
            ha=round(float(farm.area), 2) if farm.area else 0.0,
            crop=farm.current_crop or "Not specified",
            moist=soil_m,
            lst=round(temp_c, 1) if temp_c is not None else None,
            ndvi=round(ndvi, 2) if ndvi is not None else None,
            status=plot_status
        )
    ]

    # Generate Alerts
    ee_status = analysis.get("integration", {}).get("earth_engine_status", {})
    ee_ready = bool(ee_status.get("initialized"))
    alerts = alert_service.generate_farm_alerts(
        farm=farm,
        latest_moisture=soil_m,
        recent_rainfall=rain_val,
        recent_temp_c=temp_c,
        latest_ndvi=ndvi,
        observation_period=obs_dates.get("SMAP") or obs_dates.get("NASA POWER"),
        ee_authenticated=ee_ready
    )

    dataset_status_map = {
        name: d.get("status", "unknown") for name, d in datasets.items()
    }

    return DashboardResponse(
        farm_id=farm.id,
        farm_name=farm.name,
        location=farm.location,
        latitude=farm.latitude,
        longitude=farm.longitude,
        area=farm.area,
        area_unit=farm.area_unit,
        current_crop=farm.current_crop,
        soil_type=farm.soil_type,
        water_source=farm.water_source,
        irrigation_method=farm.irrigation_method,
        primary_goal=farm.primary_goal,
        plots=plots,
        conditions=conditions,
        recommended_actions=alerts,
        datasets_status=dataset_status_map,
        caveats=(
            "SMAP is a regional ~9 km model assimilation product. Landsat provides 30 m optical indices when cloud-free. "
            "NASA POWER provides daily 1/2° agroclimatology. Missing satellite passes are shown as missing observations."
        )
    )
