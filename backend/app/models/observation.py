from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class SatelliteCache(Base):
    __tablename__ = "satellite_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    farm_id = Column(String(36), ForeignKey("farms.id", ondelete="CASCADE"), nullable=False, index=True)
    dataset = Column(String(50), nullable=False, index=True)
    start_date = Column(String(20), nullable=False)
    end_date = Column(String(20), nullable=False)
    status = Column(String(50), nullable=False, default="ok")
    data_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    farm = relationship("Farm", back_populates="observations")
