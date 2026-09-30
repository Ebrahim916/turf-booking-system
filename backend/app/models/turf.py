"""Turf and availability-schedule models."""

import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.user import User

if TYPE_CHECKING:
    from app.models.booking import Booking


class Turf(TimestampMixin, Base):
    __tablename__ = "turbs"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(1000))
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    city: Mapped[str | None] = mapped_column(String(100), index=True)
    size: Mapped[str | None] = mapped_column(String(50), nullable=False, default="5-a-side")
    surface: Mapped[str | None] = mapped_column(String(50))

    price_per_hour: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    slot_duration_minutes: Mapped[int] = mapped_column(Integer, default=60, server_default="60")

    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    owner: Mapped[User] = relationship(back_populates="turfs", lazy="joined")
    schedules: Mapped[list["TurfSchedule"]] = relationship(
        back_populates="turf",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="TurfSchedule.day_of_week",
    )
    bookings: Mapped[list["Booking"]] = relationship(
        back_populates="turf", cascade="all, delete-orphan", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<Turf {self.name!r}>"


class TurfSchedule(Base):
    """Recurring weekly availability window for a turf.

    Slot generation walks these windows; the database additionally prevents two
    windows from overlapping on the same day via an exclusion constraint.
    """

    __tablename__ = "turf_schedules"
    __table_args__ = (
        UniqueConstraint("turf_id", "day_of_week", name="turf_id_day_of_week"),
        CheckConstraint("day_of_week >= 0 AND day_of_week <= 6", name="day_of_week_in_range"),
        CheckConstraint("close_time > open_time", name="close_after_open"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    turf_id: Mapped[int] = mapped_column(
        ForeignKey("turbs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 0 = Monday ... 6 = Sunday, matching datetime.date.weekday().
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    open_time: Mapped[datetime.time] = mapped_column(Time(timezone=False), nullable=False)
    close_time: Mapped[datetime.time] = mapped_column(Time(timezone=False), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    turf: Mapped[Turf] = relationship(back_populates="schedules", lazy="select")

    def __repr__(self) -> str:
        return f"<TurfSchedule turf_id={self.turf_id} day={self.day_of_week}>"
