from sqlalchemy import Column, Integer, String, Float, Date, UniqueConstraint
from src.backend.database import Base


class DailyFeatures(Base):
    """One row per park per day — raw inputs for rolling feature computation."""

    __tablename__ = "daily_features"
    __table_args__ = (UniqueConstraint("park", "date", name="uq_park_date"),)

    id            = Column(Integer, primary_key=True, index=True)
    park          = Column(String, nullable=False, index=True)
    date          = Column(Date,   nullable=False, index=True)

    # Climate (Open-Meteo)
    precipitation  = Column(Float, nullable=True)   # mm/day
    temp_max       = Column(Float, nullable=True)   # °C
    temp_min       = Column(Float, nullable=True)   # °C
    humidity_max   = Column(Float, nullable=True)   # %
    wind_speed_max = Column(Float, nullable=True)   # km/h

    # Satellite (Sentinel-2, sparse — forward-filled up to 7 days in job)
    ndvi           = Column(Float, nullable=True)

    # Fire (FIRMS / MODIS)
    firms_count    = Column(Integer, nullable=True)