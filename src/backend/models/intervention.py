from sqlalchemy import Column, Integer, String, Float
from src.backend.database import Base


class InterventionCatalog(Base):
    __tablename__ = "intervention_catalog"

    id                   = Column(String, primary_key=True)   # e.g. "fire_patrol"
    name                 = Column(String, nullable=False)
    type                 = Column(String, nullable=False)
    cost_usd             = Column(Float, nullable=False)
    max_units            = Column(Integer, nullable=False)
    effectiveness_fire   = Column(Float, nullable=False, default=0.0)
    effectiveness_drought = Column(Float, nullable=False, default=0.0)
    effectiveness_veg    = Column(Float, nullable=False, default=0.0)
    citation             = Column(String, nullable=True)