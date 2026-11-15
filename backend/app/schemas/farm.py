from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field, ConfigDict


class FarmBase(BaseModel):
    name: str = Field(..., description="Farm name")
    farmer_name: Optional[str] = Field(None, description="Farmer name")
    location: str = Field(..., description="City, region, district or country")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="WGS84 latitude")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="WGS84 longitude")
    area: Optional[float] = Field(None, ge=0.0, description="Farm area")
    area_unit: Optional[str] = Field("Acres", description="Area unit (Acres, Hectares, Square metres)")
    current_crop: Optional[str] = Field(None, description="Current primary crop")
    soil_type: Optional[str] = Field("Unknown", description="Soil type")
    water_source: Optional[str] = Field("Unknown", description="Primary water source")
    irrigation_method: Optional[str] = Field("Unknown", description="Irrigation method")
    primary_goal: Optional[str] = Field("Increase Crop Yield & Quality", description="Primary farming goal")
    timezone: Optional[str] = Field("Asia/Kolkata", description="Farm local timezone")
    climate_zone: Optional[str] = Field(None, description="Climate zone (trop, humid, med, temp)")
    boundary_geojson: Optional[Any] = Field(None, description="GeoJSON geometry, polygon coordinates, or boundary points")
    plots_json: Optional[Any] = Field(None, description="Sub-plots information")


class FarmCreate(FarmBase):
    pass


class FarmUpdate(BaseModel):
    name: Optional[str] = None
    farmer_name: Optional[str] = None
    location: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    area: Optional[float] = Field(None, ge=0.0)
    area_unit: Optional[str] = None
    current_crop: Optional[str] = None
    soil_type: Optional[str] = None
    water_source: Optional[str] = None
    irrigation_method: Optional[str] = None
    primary_goal: Optional[str] = None
    timezone: Optional[str] = None
    climate_zone: Optional[str] = None
    boundary_geojson: Optional[Any] = None
    plots_json: Optional[Any] = None


class FarmResponse(FarmBase):
    id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
