from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Numeric, DateTime, ForeignKey,
    UniqueConstraint, ForeignKeyConstraint,
)
from src.backend.database import Base


class Recommendation(Base):
    """A persisted ILP recommendation for a park at a point in time."""

    __tablename__ = "recommendations"

    id              = Column(Integer, primary_key=True, index=True)
    park_id         = Column(String, nullable=False, index=True)
    user_id         = Column(Integer, ForeignKey("users.id"), nullable=True)
    budget          = Column(Numeric(12, 2), nullable=False)
    total_cost      = Column(Numeric(12, 2), nullable=False, default=0)
    total_risk_reduction = Column(Numeric(8, 6), nullable=False, default=0)
    created_at      = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class Allocation(Base):
    """One line item: N units of an intervention assigned to a zone under a recommendation.

    Three-way junction between Recommendation, Intervention, and Zone.
    The composite FK (park_id, zone_id) prevents an allocation from pointing
    to a zone that belongs to a different park than the recommendation.
    """

    __tablename__ = "allocations"
    __table_args__ = (
        UniqueConstraint("recommendation_id", "intervention_id", "zone_id",
                         name="uq_alloc_rec_int_zone"),
        ForeignKeyConstraint(["park_id", "zone_id"], ["zones.park_id", "zones.id"],
                             name="fk_alloc_zone_park"),
    )

    id                = Column(Integer, primary_key=True, index=True)
    recommendation_id = Column(Integer, ForeignKey("recommendations.id"), nullable=False, index=True)
    intervention_id   = Column(String, ForeignKey("intervention_catalog.id"), nullable=False)
    park_id           = Column(String, nullable=False)
    zone_id           = Column(Integer, nullable=False)
    units             = Column(Integer, nullable=False)
    total_cost        = Column(Numeric(12, 2), nullable=False)