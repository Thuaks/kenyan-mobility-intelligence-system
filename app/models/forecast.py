"""
app/models/forecast.py
Stores computed demand forecasts per route per hour.
Written by the ML pipeline, read by the API.
"""
from datetime import datetime, timezone
from sqlalchemy import String, Float, Integer, DateTime, Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class DemandForecast(Base):
    __tablename__ = "demand_forecasts"

    id: Mapped[int] = mapped_column(primary_key=True)
    route_id: Mapped[str] = mapped_column(
        String(10), ForeignKey("routes.route_id"), index=True, nullable=False
    )
    forecast_date: Mapped[datetime] = mapped_column(Date, nullable=False, index=True)
    hour: Mapped[int] = mapped_column(Integer, nullable=False)

    # Prophet outputs
    yhat: Mapped[float] = mapped_column(Float, nullable=False)         # point forecast
    yhat_lower: Mapped[float] = mapped_column(Float, nullable=True)    # lower CI
    yhat_upper: Mapped[float] = mapped_column(Float, nullable=True)    # upper CI

    # XGBoost output
    xgb_yhat: Mapped[float] = mapped_column(Float, nullable=True)

    model_version: Mapped[str] = mapped_column(String(50), nullable=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self):
        return (
            f"<DemandForecast route={self.route_id} "
            f"date={self.forecast_date} hour={self.hour} yhat={self.yhat:.0f}>"
        )
