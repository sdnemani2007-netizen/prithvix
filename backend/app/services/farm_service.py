import json
import uuid
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.farm import Farm
from app.schemas.farm import FarmCreate, FarmUpdate
from app.utils.geo import zone_for, parse_boundary_to_geojson, compute_centroid_and_area


def list_farms(db: Session) -> List[Farm]:
    """Retrieve all saved farm profiles."""
    return db.query(Farm).order_by(Farm.created_at.desc()).all()


def get_farm_by_id(db: Session, farm_id: str) -> Optional[Farm]:
    """Retrieve a single farm by ID."""
    return db.query(Farm).filter(Farm.id == farm_id).first()


def create_farm(db: Session, farm_in: FarmCreate) -> Farm:
    """Create a new persistent farm record."""
    zone = farm_in.climate_zone or zone_for(farm_in.latitude)

    # Normalize GeoJSON geometry
    geojson = parse_boundary_to_geojson(farm_in.boundary_geojson, farm_in.latitude, farm_in.longitude)
    c_lat, c_lon, computed_area_km2 = compute_centroid_and_area(geojson, farm_in.latitude, farm_in.longitude)

    area = farm_in.area
    area_unit = farm_in.area_unit or "Acres"
    if area is None or area <= 0:
        # Default based on computed geometry
        if area_unit == "Hectares":
            area = round(computed_area_km2 * 100.0, 2)
        elif area_unit == "Square metres":
            area = round(computed_area_km2 * 1_000_000.0, 1)
        else:
            area = round(computed_area_km2 * 247.105, 2)

    farm = Farm(
        id=str(uuid.uuid4()),
        name=farm_in.name,
        farmer_name=farm_in.farmer_name,
        location=farm_in.location,
        latitude=farm_in.latitude,
        longitude=farm_in.longitude,
        area=area,
        area_unit=area_unit,
        current_crop=farm_in.current_crop,
        soil_type=farm_in.soil_type or "Unknown",
        water_source=farm_in.water_source or "Unknown",
        irrigation_method=farm_in.irrigation_method or "Unknown",
        primary_goal=farm_in.primary_goal or "Increase Crop Yield & Quality",
        timezone=farm_in.timezone or "Asia/Kolkata",
        climate_zone=zone,
        boundary_geojson=json.dumps(geojson) if geojson else None,
        plots_json=json.dumps(farm_in.plots_json) if farm_in.plots_json else None
    )
    db.add(farm)
    db.commit()
    db.refresh(farm)
    return farm


def update_farm(db: Session, farm_id: str, farm_in: FarmUpdate) -> Optional[Farm]:
    """Update an existing farm record."""
    farm = get_farm_by_id(db, farm_id)
    if not farm:
        return None

    update_data = farm_in.model_dump(exclude_unset=True)

    if "latitude" in update_data and update_data["latitude"] is not None and "climate_zone" not in update_data:
        update_data["climate_zone"] = zone_for(update_data["latitude"])

    if "boundary_geojson" in update_data and update_data["boundary_geojson"] is not None:
        geojson = parse_boundary_to_geojson(
            update_data["boundary_geojson"],
            update_data.get("latitude", farm.latitude),
            update_data.get("longitude", farm.longitude)
        )
        update_data["boundary_geojson"] = json.dumps(geojson)

    if "plots_json" in update_data and update_data["plots_json"] is not None:
        update_data["plots_json"] = json.dumps(update_data["plots_json"])

    for field, value in update_data.items():
        setattr(farm, field, value)

    db.commit()
    db.refresh(farm)
    return farm


def delete_farm(db: Session, farm_id: str) -> bool:
    """Delete a farm and its associated records."""
    farm = get_farm_by_id(db, farm_id)
    if not farm:
        return False
    db.delete(farm)
    db.commit()
    return True
