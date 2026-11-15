import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGINS
from app.database import init_db
from app.services.earth_engine import initialize_earth_engine
from app.routers import (
    health,
    farms,
    dashboard,
    satellite,
    weather,
    crops,
    irrigation,
    alerts,
    chat,
)

logger = logging.getLogger("prithvix")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize Database
    logger.info("Initializing PrithviX database tables...")
    init_db()
    initialize_earth_engine()
    yield
    # Shutdown
    logger.info("PrithviX backend shutting down.")


app = FastAPI(
    title="PrithviX Geospatial & Agricultural Intelligence API",
    version="1.0.0",
    description="NASA Earth observation data-driven agricultural intelligence platform.",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Accept", "Authorization", "Content-Type"],
)

# Include Routers
app.include_router(health.router)
app.include_router(farms.router)
app.include_router(dashboard.router)
app.include_router(satellite.router)
app.include_router(weather.router)
app.include_router(crops.router)
app.include_router(irrigation.router)
app.include_router(alerts.router)
app.include_router(chat.router)


@app.get("/")
def root():
    return {
        "message": "Welcome to PrithviX API. Visit /docs for the interactive Swagger documentation.",
        "status": "online"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=False)

