"""Booking model.

The `no_overlapping_bookings` exclusion constraint is created in the Alembic
migration rather than in `__table_args__` because it requires the `btree_gist`
extension and a `tstzrange` expression that SQLAlchemy cannot express natively.
That constraint - not application logic - is the authority on double-booking.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import BookingStatus, PaymentStatus
from app.models.turf import Turf
from app.models.user import User


class Booking(TimestampMixin, Base):
    __tablename__ = "bookings"
    __table_args__ = (
        CheckConstraint("end_time > start_time", name="end_after_start"),
        CheckConstraint("total_price >= 0", name="total_price_non_negative"),
        Index("ix_bookings_user_start", "user_id", "start_time"),
        Index("ix_bookings_turf_start", "turf_id", "start_time"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    turf_id: Mapped[int] = mapped_column(ForeignKey("turbs.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    status: Mapped[BookingStatus] = mapped_column(
        String(16), default=BookingStatus.CONFIRMED, server_default="confirmed", nullable=False
    )
    payment_status: Mapped[PaymentStatus] = mapped_column(
        String(16), default=PaymentStatus.UNPAID, server_default="unpaid", nullable=False
    )
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    total_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    # Audit trail of status changes: [{"from": ..., "to": ..., "at": ..., "by": ...}]
    status_history: Mapped[list[dict[str, object]] | None] = mapped_column(
        JSONB, default=list
    )

    turf: Mapped[Turf] = relationship(back_populates="bookings", lazy="joined")
    user: Mapped[User] = relationship(back_populates="bookings", lazy="joined")

    @property
    def duration_hours(self) -> Decimal:
        seconds = (self.end_time - self.start_time).total_seconds()
        return Decimal(seconds) / Decimal(3600)

    def __repr__(self) -> str:
        return f"<Booking id={self.id} turf_id={self.turf_id} status={self.status}>"
