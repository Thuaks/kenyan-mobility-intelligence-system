"""
app/models/alert.py
Tracks outbound SMS alerts sent via Africa's Talking.
"""
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    alert_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # risk_change | demand_spike | heavy_rain
    route_id: Mapped[str] = mapped_column(
        String(10), ForeignKey("routes.route_id"), nullable=True, index=True
    )
    recipient_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # Delivery status
    sent: Mapped[bool] = mapped_column(Boolean, default=False)
    delivered: Mapped[bool] = mapped_column(Boolean, default=False)
    at_message_id: Mapped[str] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)

    triggered_by: Mapped[str] = mapped_column(String(100), nullable=True)  # scheduler | api
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<Alert id={self.id} type={self.alert_type} route={self.route_id} sent={self.sent}>"
