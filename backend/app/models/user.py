"""User and refresh-token models."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base, TimestampMixin
from app.models.role import Role

if TYPE_CHECKING:
    from app.models.booking import Booking
    from app.models.turf import Turf


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20))

    role_id: Mapped[int] = mapped_column(
        ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    role: Mapped[Role] = relationship(back_populates="users", lazy="joined")
    turfs: Mapped[list["Turf"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan", lazy="select"
    )
    bookings: Mapped[list["Booking"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="select"
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="select"
    )

    @property
    def is_admin(self) -> bool:
        return self.role is not None and self.role.name == "admin"

    def __repr__(self) -> str:
        return f"<User {self.email}>"


class RefreshToken(Base):
    """Server-side session record backing the opaque refresh cookie.

    Only a SHA-256 hash of the token is stored, so a database leak cannot be
    replayed as a valid session. `replaced_by_id` links each rotation so a reused
    (already revoked) token can be traced back and the whole family killed.
    """

    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replaced_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("refresh_tokens.id", ondelete="SET NULL"), nullable=True
    )
    user_agent: Mapped[str | None] = mapped_column(String(255))
    ip_address: Mapped[str | None] = mapped_column(String(45))

    user: Mapped[User] = relationship(back_populates="refresh_tokens", lazy="joined")
    replaced_by: Mapped["RefreshToken | None"] = relationship(
        remote_side="RefreshToken.id", lazy="select"
    )

    @property
    def is_active(self) -> bool:
        from datetime import UTC, datetime

        return self.revoked_at is None and self.expires_at > datetime.now(UTC)

    def __repr__(self) -> str:
        return f"<RefreshToken user_id={self.user_id} active={self.is_active}>"
