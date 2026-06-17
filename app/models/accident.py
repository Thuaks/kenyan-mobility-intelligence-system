"""
app/models/accident.py
Individual accident records ingested from NTSA / ACLED sources.
"""
from datetime import datetime, date, timezone
from sqlalchemy import String, Float, Integer, Date, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class Accident(Base):
    __tablename__ = "accidents"

    id: Mapped[int] = mapped_column(primary_key=True)
    accident_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    hour: Mapped[int] = mapped_column(Integer, nullable=True)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=True)

    # Location
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    sub_county: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    route_id: Mapped[str] = mapped_column(
        String(10), ForeignKey("routes.route_id"), nullable=True, index=True
    )

    # Classification
    accident_type: Mapped[str] = mapped_column(String(100), nullable=True)
    cause: Mapped[str] = mapped_column(String(100), nullable=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=True, index=True)
    vehicles_involved: Mapped[int] = mapped_column(Integer, nullable=True)
    casualties: Mapped[int] = mapped_column(Integer, default=0)

    # Conditions
    road_surface: Mapped[str] = mapped_column(String(50), nullable=True)
    lighting: Mapped[str] = mapped_column(String(50), nullable=True)
    weather_condition: Mapped[str] = mapped_column(String(50), nullable=True)
    is_peak_hour: Mapped[bool] = mapped_column(Boolean, default=False)

    # Cluster assignment (from DBSCAN)
    cluster_id: Mapped[int] = mapped_column(Integer, nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self):
        return f"<Accident {self.accident_id} | {self.severity} | {self.date}>"
