"""Booking schemas."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.models.enums import BookingStatus, PaymentStatus
from app.schemas.common import ORMModel, TimestampedSchema


class BookingCreate(BaseModel):
    turf_id: int
    start_time: datetime
    end_time: datetime | None = Field(
        default=None,
        description="Optional. Derived from the turf's slot duration when omitted.",
    )
    notes: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def check_window(self) -> "BookingCreate":
        if self.end_time is not None and self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time.")
        return self


class BookingRead(ORMModel):
    id: int
    turf_id: int
    turf_name: str | None = None
    user_id: int
    user_name: str | None = None
    start_time: datetime
    end_time: datetime
    status: BookingStatus
    payment_status: PaymentStatus
    total_price: Decimal
    notes: str | None


class BookingReadDetailed(TimestampedSchema, BookingRead):
    price_per_hour: Decimal | None = None
    address: str | None = None
    paid_at: datetime | None = None


class BookingUpdate(BaseModel):
    """Admin-only status transitions and payment capture at the venue."""

    status: BookingStatus | None = None
    payment_status: PaymentStatus | None = None
    notes: str | None = Field(default=None, max_length=500)
