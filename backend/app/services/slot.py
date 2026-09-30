"""Availability and slot generation.

Slots are derived from a turf's weekly `TurfSchedule` windows and its
`slot_duration_minutes`, then marked unavailable when they overlap an existing
pending/confirmed booking or fall in the past.
"""

from datetime import UTC, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError
from app.models.booking import Booking
from app.models.enums import BookingStatus
from app.models.turf import Turf
from app.schemas.turf import SlotRead

MAX_DAYS_AHEAD = 60


def _naive_utc(day: datetime, moment: time) -> datetime:
    return datetime.combine(day.date(), moment, tzinfo=UTC)


def overlaps(start_a: datetime, end_a: datetime, start_b: datetime, end_b: datetime) -> bool:
    """Half-open interval overlap: [start, end). Touching endpoints do not overlap."""
    return start_a < end_b and start_b < end_a


def price_for(price_per_hour: Decimal, start: datetime, end: datetime) -> Decimal:
    """Pro-rate a booking's price from the hourly rate."""
    hours = Decimal((end - start).total_seconds()) / Decimal(3600)
    return (price_per_hour * hours).quantize(Decimal("0.01"))


async def get_booked_windows(
    db: AsyncSession, turf_id: int, window_start: datetime, window_end: datetime
) -> list[tuple[datetime, datetime]]:
    """Return [start, end) ranges that block the turf within the query window."""
    # `db.execute`, not `db.scalars`: a two-column select must return row tuples,
    # whereas scalars would yield only the first column of each row.
    result = await db.execute(
        select(Booking.start_time, Booking.end_time).where(
            Booking.turf_id == turf_id,
            Booking.status.in_([BookingStatus.PENDING, BookingStatus.CONFIRMED]),
            Booking.start_time < window_end,
            Booking.end_time > window_start,
        )
    )
    return [(row.start_time, row.end_time) for row in result]


async def generate_slots(
    db: AsyncSession, turf: Turf, on_date: datetime, *, include_past: bool = False
) -> list[SlotRead]:
    """Build the slot list for one calendar day in UTC.

    Schedules use `weekday()` semantics (0 = Monday), so a Sunday maps to 6.
    """
    if on_date.tzinfo is None:
        on_date = on_date.replace(tzinfo=UTC)
    on_date = on_date.astimezone(UTC)

    if on_date.date() > (datetime.now(UTC) + timedelta(days=MAX_DAYS_AHEAD)).date():
        raise ValidationError(f"Cannot view availability more than {MAX_DAYS_AHEAD} days ahead.")

    day_of_week = on_date.weekday()
    windows = [s for s in turf.schedules if s.day_of_week == day_of_week and s.is_active]
    if not windows:
        return []

    earliest = min(_naive_utc(on_date, w.open_time) for w in windows)
    latest = max(_naive_utc(on_date, w.close_time) for w in windows)
    booked = await get_booked_windows(db, turf.id, earliest, latest)

    now = datetime.now(UTC)
    duration = timedelta(minutes=turf.slot_duration_minutes)
    slots: list[SlotRead] = []

    for window in windows:
        start = _naive_utc(on_date, window.open_time)
        close = _naive_utc(on_date, window.close_time)

        while start + duration <= close:
            end = start + duration
            is_past = end <= now
            taken = any(overlaps(start, end, b_start, b_end) for b_start, b_end in booked)
            slots.append(
                SlotRead(
                    start_time=start,
                    end_time=end,
                    is_available=not is_past and not taken,
                    total_price=price_for(turf.price_per_hour, start, end),
                )
            )
            start = end

    slots.sort(key=lambda s: s.start_time)
    return slots
