from datetime import date, datetime
from sqlalchemy import Column, Integer, String, Float, Date, DateTime
from src.backend.database import Base


class Forecast(Base):
    __tablename__ = "forecasts"

    id          = Column(Integer, primary_key=True, index=True)
    park        = Column(String, nullable=False, index=True)
    date        = Column(Date, nullable=False, index=True)
    fire_prob   = Column(Float, nullable=False)
    drought_prob = Column(Float, nullable=False)
    veg_prob    = Column(Float, nullable=False)
    computed_at = Column(DateTime, default=datetime.utcnow, nullable=False)