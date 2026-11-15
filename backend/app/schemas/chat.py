from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class FarmContextPayload(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timezone: Optional[str] = None
    zone: Optional[str] = None
    currentCrop: Optional[str] = None
    soilType: Optional[str] = None
    waterSource: Optional[str] = None
    irrigation: Optional[str] = None
    farmArea: Optional[str] = None
    areaUnit: Optional[str] = None
    primaryGoal: Optional[str] = None


class ChatRequest(BaseModel):
    message: str = Field(..., description="User question or agricultural inquiry")
    farm: Optional[FarmContextPayload] = Field(None, description="Farm profile context sent from frontend")
    farm_id: Optional[str] = Field(None, description="Optional farm ID to load database state")


class ChatResponse(BaseModel):
    reply: str
    grounded_on: Optional[Dict[str, Any]] = None
    provider: Optional[str] = "PrithviX Agronomy AI"
