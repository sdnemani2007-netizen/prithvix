from fastapi import APIRouter
from app.services.earth_engine import get_earth_engine_status

router = APIRouter(tags=["Health"])


@router.get("/health")
@router.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "service": "PrithviX Geospatial API",
        "version": "1.0.0",
        "earth_engine": get_earth_engine_status()
    }
