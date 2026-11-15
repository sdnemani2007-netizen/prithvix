from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class DatasetMetadata(BaseModel):
    name: str
    source_id: Optional[str] = None
    nominal_scale_m: Optional[float] = None
    temporal_resolution: Optional[str] = None
    units: Optional[Dict[str, str]] = None
    caveat: Optional[str] = None


class DatasetResult(BaseModel):
    status: str = Field(..., description="ok | no_data | auth_required | error")
    source: str
    source_id: Optional[str] = None
    nominal_scale_m: Optional[float] = None
    temporal_resolution: Optional[str] = None
    units: Optional[Dict[str, str]] = None
    caveat: Optional[str] = None
    records: List[Dict[str, Any]] = Field(default_factory=list)
    message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SatelliteAnalysisResponse(BaseModel):
    ok: bool
    request_id: str
    farm_id: Optional[str] = None
    aoi: Dict[str, Any]
    period: Dict[str, str]
    datasets: Dict[str, DatasetResult]
    summary: Dict[str, Any]
    warnings: List[str] = Field(default_factory=list)
    errors: List[Dict[str, str]] = Field(default_factory=list)
    integration: Dict[str, Any]
