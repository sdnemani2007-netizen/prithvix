import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.farm import Farm
from app.schemas.farm import FarmCreate, FarmUpdate, FarmResponse
from app.services import farm_service

router = APIRouter(prefix="/api/farms", tags=["Farms"])


@router.get("", response_model=List[FarmResponse])
def get_farms(db: Session = Depends(get_db)):
    """Retrieve all saved farm profiles."""
    farms = farm_service.list_farms(db)
    results = []
    for f in farms:
        boundary = None
        if f.boundary_geojson:
            try:
                boundary = json.loads(f.boundary_geojson)
            except Exception:
                boundary = f.boundary_geojson
        plots = None
        if f.plots_json:
            try:
                plots = json.loads(f.plots_json)
            except Exception:
                plots = f.plots_json

        results.append(FarmResponse(
            id=f.id,
            name=f.name,
            farmer_name=f.farmer_name,
            location=f.location,
            latitude=f.latitude,
            longitude=f.longitude,
            area=f.area,
            area_unit=f.area_unit,
            current_crop=f.current_crop,
            soil_type=f.soil_type,
            water_source=f.water_source,
            irrigation_method=f.irrigation_method,
            primary_goal=f.primary_goal,
            timezone=f.timezone,
            climate_zone=f.climate_zone,
            boundary_geojson=boundary,
            plots_json=plots,
            created_at=f.created_at,
            updated_at=f.updated_at
        ))
    return results


@router.post("", response_model=FarmResponse, status_code=status.HTTP_201_CREATED)
def create_farm(farm_in: FarmCreate, db: Session = Depends(get_db)):
    """Create a new farm profile."""
    try:
        farm = farm_service.create_farm(db, farm_in)
        boundary = None
        if farm.boundary_geojson:
            try:
                boundary = json.loads(farm.boundary_geojson)
            except Exception:
                boundary = farm.boundary_geojson
        plots = None
        if farm.plots_json:
            try:
                plots = json.loads(farm.plots_json)
            except Exception:
                plots = farm.plots_json

        return FarmResponse(
            id=farm.id,
            name=farm.name,
            farmer_name=farm.farmer_name,
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
            timezone=farm.timezone,
            climate_zone=farm.climate_zone,
            boundary_geojson=boundary,
            plots_json=plots,
            created_at=farm.created_at,
            updated_at=farm.updated_at
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to create farm: {exc}")


@router.get("/{farm_id}", response_model=FarmResponse)
def get_farm(farm_id: str, db: Session = Depends(get_db)):
    """Retrieve details for a specific farm."""
    farm = farm_service.get_farm_by_id(db, farm_id)
    if not farm:
        raise HTTPException(status_code=404, detail=f"Farm '{farm_id}' not found.")

    boundary = None
    if farm.boundary_geojson:
        try:
            boundary = json.loads(farm.boundary_geojson)
        except Exception:
            boundary = farm.boundary_geojson
    plots = None
    if farm.plots_json:
        try:
            plots = json.loads(farm.plots_json)
        except Exception:
            plots = farm.plots_json

    return FarmResponse(
        id=farm.id,
        name=farm.name,
        farmer_name=farm.farmer_name,
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
        timezone=farm.timezone,
        climate_zone=farm.climate_zone,
        boundary_geojson=boundary,
        plots_json=plots,
        created_at=farm.created_at,
        updated_at=farm.updated_at
    )


@router.put("/{farm_id}", response_model=FarmResponse)
def update_farm(farm_id: str, farm_in: FarmUpdate, db: Session = Depends(get_db)):
    """Update a farm profile."""
    farm = farm_service.update_farm(db, farm_id, farm_in)
    if not farm:
        raise HTTPException(status_code=404, detail=f"Farm '{farm_id}' not found.")

    boundary = None
    if farm.boundary_geojson:
        try:
            boundary = json.loads(farm.boundary_geojson)
        except Exception:
            boundary = farm.boundary_geojson
    plots = None
    if farm.plots_json:
        try:
            plots = json.loads(farm.plots_json)
        except Exception:
            plots = farm.plots_json

    return FarmResponse(
        id=farm.id,
        name=farm.name,
        farmer_name=farm.farmer_name,
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
        timezone=farm.timezone,
        climate_zone=farm.climate_zone,
        boundary_geojson=boundary,
        plots_json=plots,
        created_at=farm.created_at,
        updated_at=farm.updated_at
    )


@router.delete("/{farm_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_farm(farm_id: str, db: Session = Depends(get_db)):
    """Delete a farm profile."""
    success = farm_service.delete_farm(db, farm_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Farm '{farm_id}' not found.")
    return None
