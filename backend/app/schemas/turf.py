"""Turf and schedule schemas."""

from datetime import datetime, time
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import ORMModel, TimestampedSchema


class ScheduleCreate(BaseModel):
    day_of_week: int = Field(ge=0, le=6, description="0 = Monday ... 6 = Sunday")
    open_time: time
    close_time: time

    @model_validator(mode="after")
    def check_window(self) -> "ScheduleCreate":
        if self.open_time >= self.close_time:
            raise ValueError("open_time must be earlier than close_time.")
        return self


class ScheduleUpdate(BaseModel):
    open_time: time | None = None
    close_time: time | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def check_window(self) -> "ScheduleUpdate":
        if (
            self.open_time is not None
            and self.close_time is not None
            and self.open_time >= self.close_time
        ):
            raise ValueError("open_time must be earlier than close_time.")
        return self


class ScheduleRead(ORMModel):
    id: int
    day_of_week: int
    open_time: time
    close_time: time
    is_active: bool


class TurfCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=1000)
    address: str = Field(min_length=5, max_length=500)
    city: str | None = Field(default=None, max_length=100)
    size: str = Field(default="5-a-side", max_length=50)
    surface: str | None = Field(default=None, max_length=50)
    price_per_hour: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    slot_duration_minutes: int = Field(default=60, ge=15, le=480)


class TurfUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=1000)
    address: str | None = Field(default=None, min_length=5, max_length=500)
    city: str | None = Field(default=None, max_length=100)
    size: str | None = Field(default=None, max_length=50)
    surface: str | None = Field(default=None, max_length=50)
    price_per_hour: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    slot_duration_minutes: int | None = Field(default=None, ge=15, le=480)
    is_active: bool | None = None


class TurfRead(ORMModel):
    id: int
    name: str
    description: str | None
    address: str
    city: str | None
    size: str
    surface: str | None
    price_per_hour: Decimal
    slot_duration_minutes: int
    owner_id: int
    is_active: bool
    schedules: list[ScheduleRead] = Field(default_factory=list)


class TurfReadDetailed(TimestampedSchema, TurfRead):
    owner_name: str | None = None


class TurfListItem(ORMModel):
    id: int
    name: str
    address: str
    city: str | None
    size: str
    surface: str | None
    price_per_hour: Decimal
    owner_id: int
    is_active: bool


class SlotRead(BaseModel):
    """A generated bookable slot. `is_available` is False when the slot is in
    the past or overlaps an existing pending/confirmed booking."""

    start_time: datetime
    end_time: datetime
    is_available: bool
    total_price: Decimal
