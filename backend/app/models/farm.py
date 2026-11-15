import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Text, DateTime
from sqlalchemy.orm import relationship
from app.database import Base


class Farm(Base):
    __tablename__ = "farms"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, index=True)
    farmer_name = Column(String(255), nullable=True)
    location = Column(String(255), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    area = Column(Float, nullable=True)
    area_unit = Column(String(50), default="Acres")
    current_crop = Column(String(100), nullable=True)
    soil_type = Column(String(100), default="Unknown")
    water_source = Column(String(100), default="Unknown")
    irrigation_method = Column(String(100), default="Unknown")
    primary_goal = Column(String(255), default="Increase Crop Yield & Quality")
    timezone = Column(String(100), default="Asia/Kolkata")
    climate_zone = Column(String(50), default="trop")
    boundary_geojson = Column(Text, nullable=True)
    plots_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationship to cached satellite observations
    observations = relationship("SatelliteCache", back_populates="farm", cascade="all, delete-orphan")
