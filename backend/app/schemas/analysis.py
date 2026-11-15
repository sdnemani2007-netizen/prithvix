from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class PlotCondition(BaseModel):
    id: str
    name: str
    ha: float
    crop: str
    moist: Optional[float] = None
    lst: Optional[float] = None
    ndvi: Optional[float] = None
    status: str


class AlertItem(BaseModel):
    s: str = Field(..., description="Severity: 'c' (Critical), 'w' (Warning), 'i' (Info), 'n' (Normal)")
    t: str = Field(..., description="Alert Title")
    p: str = Field(..., description="Plot / Sector identifier (e.g. 'A', 'B', 'All')")
    d: str = Field(..., description="Formatted Date / Observation Timestamp")
    x: str = Field(..., description="Description / Observation Details")
    a: str = Field(..., description="Suggested Action")
    source: Optional[str] = Field(None, description="Dataset source attribution (e.g. SMAP, GPM)")


class DashboardConditions(BaseModel):
    soil_moisture: Optional[float] = None
    soil_moisture_str: str = "--"
    vegetation_ndvi: Optional[float] = None
    vegetation_ndvi_str: str = "--"
    water_available: Optional[float] = None
    water_available_status: str = "Unknown"
    surface_temp_c: Optional[float] = None
    surface_temp_str: str = "--"
    observation_dates: Dict[str, str] = Field(default_factory=dict)
    sources: Dict[str, str] = Field(default_factory=dict)


class DashboardResponse(BaseModel):
    farm_id: str
    farm_name: str
    location: str
    latitude: float
    longitude: float
    area: Optional[float] = None
    area_unit: Optional[str] = "Acres"
    current_crop: Optional[str] = None
    soil_type: Optional[str] = None
    water_source: Optional[str] = None
    irrigation_method: Optional[str] = None
    primary_goal: Optional[str] = None
    plots: List[PlotCondition] = Field(default_factory=list)
    conditions: DashboardConditions
    recommended_actions: List[AlertItem] = Field(default_factory=list)
    datasets_status: Dict[str, str] = Field(default_factory=dict)
    caveats: str


class SoilClimateResponse(BaseModel):
    farm_id: str
    periods: List[str]
    moist: List[Optional[float]]
    rain: List[Optional[float]]
    lst: List[Optional[float]]
    ndvi: List[Optional[float]]
    sources: Dict[str, str]
    caveats: str


class CropRecommendation(BaseModel):
    n: str = Field(..., description="Crop name")
    sc: int = Field(..., ge=0, le=100, description="Suitability score (0-100)")
    w: str = Field(..., description="Water need: 'Low' | 'Medium' | 'High'")
    why: str = Field(..., description="Agronomic reasoning")
    supporting_observations: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    confidence: str = "Moderate"


class CropRecommendationResponse(BaseModel):
    farm_id: str
    climate_zone: str
    current_crop: Optional[str] = None
    soil_type: Optional[str] = None
    recommendations: List[CropRecommendation]
    agronomic_summary: str


class RotationPlan(BaseModel):
    A: List[str]
    B: List[str]
    note: str


class CropRotationResponse(BaseModel):
    farm_id: str
    plans: Dict[str, RotationPlan]
    agronomic_advice: str


class IrrigationAdvisoryResponse(BaseModel):
    farm_id: str
    current_soil_moisture: Optional[float] = None
    soil_moisture_status: str
    recent_rainfall_mm: Optional[float] = None
    recent_temp_c: Optional[float] = None
    advisory: str
    explanation: str
    observation_date: Optional[str] = None
    data_sources: List[str] = Field(default_factory=list)
    limitations: str
