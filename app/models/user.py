"""
app/models/user.py
User model — supports role-based access (admin, analyst, sacco_operator, public).
"""
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
import enum
from app.db.base import Base


class UserRole(str, enum.Enum):
    admin          = "admin"
    analyst        = "analyst"
    sacco_operator = "sacco_operator"
    public         = "public"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole), default=UserRole.public, nullable=False
    )
    organisation: Mapped[str] = mapped_column(String(255), nullable=True)
    phone: Mapped[str] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    last_login: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<User id={self.id} email={self.email} role={self.role}>"
