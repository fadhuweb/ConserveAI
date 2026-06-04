from sqlalchemy import Column, Integer, String, Float, UniqueConstraint
from src.backend.database import Base


class Zone(Base):
    """A geographic subdivision of a park. Each park has exactly four zones.

    Geometry is stored as a rectangular bounding box (four floats) rather than
    a PostGIS geometry, which is sufficient for Leaflet rectangle display and
    avoids a spatial-extension dependency.
    """

    __tablename__ = "zones"
    __table_args__ = (
        UniqueConstraint("park_id", "name", name="uq_zone_park_name"),
        UniqueConstraint("park_id", "id",  name="uq_zone_park_id"),   # target for allocations composite FK
    )

    id      = Column(Integer, primary_key=True, index=True)
    park_id = Column(String, nullable=False, index=True)
    name    = Column(String, nullable=False)   # e.g. "North-West"

    min_lon = Column(Float, nullable=False)
    min_lat = Column(Float, nullable=False)
    max_lon = Column(Float, nullable=False)
    max_lat = Column(Float, nullable=False)