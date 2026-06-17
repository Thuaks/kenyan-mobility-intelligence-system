"""
app/models/route.py
Route catalogue + risk score records.
"""
from datetime import datetime, timezone
from sqlalchemy import String, Float, Integer, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Route(Base):
    __tablename__ = "routes"

    id: Mapped[int] = mapped_column(primary_key=True)
    route_id: Mapped[str] = mapped_column(String(10), unique=True, index=True, nullable=False)
    route_name: Mapped[str] = mapped_column(String(255), nullable=False)
    sub_county: Mapped[str] = mapped_column(String(100), nullable=True)
    distance_km: Mapped[float] = mapped_column(Float, nullable=True)
    n_stops: Mapped[int] = mapped_column(Integer, nullable=True)
    avg_fare_ksh: Mapped[int] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # relationships
    risk_scores: Mapped[list["RouteRiskScore"]] = relationship(
        back_populates="route", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Route {self.route_id}: {self.route_name}>"


class RouteRiskScore(Base):
    __tablename__ = "route_risk_scores"

    id: Mapped[int] = mapped_column(primary_key=True)
    route_id: Mapped[str] = mapped_column(
        String(10), ForeignKey("routes.route_id"), index=True, nullable=False
    )
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False)   # 1–5
    risk_label: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=True)
    top_drivers: Mapped[dict] = mapped_column(JSON, nullable=True)      # SHAP top-3
    accidents_24mo: Mapped[int] = mapped_column(Integer, nullable=True)
    accidents_per_km: Mapped[float] = mapped_column(Float, nullable=True)
    model_version: Mapped[str] = mapped_column(String(50), nullable=True)
    scored_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    route: Mapped["Route"] = relationship(back_populates="risk_scores")
