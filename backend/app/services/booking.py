"""Booking creation, listing, and lifecycle transitions.

Double-booking is prevented by a PostgreSQL exclusion constraint, not by this
module. The overlap check here exists only to return a friendly 409 in the
common case; under concurrency the database constraint is what actually holds.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import (
    BookingConflictError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from app.models.booking import Booking
from app.models.enums import BookingStatus, PaymentStatus
from app.models.turf import Turf
from app.models.user import User
from app.schemas.booking import BookingCreate, BookingUpdate
from app.services.slot import get_booked_windows, overlaps, price_for

MAX_BOOKING_DURATION = timedelta(hours=8)
MIN_LEAD_TIME = timedelta(minutes=0)

# Which transitions the API permits, independent of who is requesting them.
ALLOWED_TRANSITIONS: dict[BookingStatus, set[BookingStatus]] = {
    BookingStatus.PENDING: {BookingStatus.CONFIRMED, BookingStatus.CANCELLED},
    BookingStatus.CONFIRMED: {BookingStatus.COMPLETED, BookingStatus.CANCELLED},
    BookingStatus.CANCELLED: set(),
    BookingStatus.COMPLETED: set(),
}


async def get_booking(db: AsyncSession, booking_id: int) -> Booking:
    booking = await db.scalar(
        select(Booking)
        .where(Booking.id == booking_id)
        .options(selectinload(Booking.turf), selectinload(Booking.user))
    )
    if booking is None:
        raise NotFoundError("Booking not found.")
    return booking


def assert_can_view(user: User, booking: Booking) -> None:
    if user.is_admin:
        return
    is_owner_of_turf = booking.turf is not None and booking.turf.owner_id == user.id
    if booking.user_id != user.id and not is_owner_of_turf:
        raise PermissionDeniedError("You do not have access to this booking.")


def _append_history(
    booking: Booking, new_status: BookingStatus, actor: User, note: str | None
) -> None:
    history = list(booking.status_history or [])
    history.append(
        {
            "from": booking.status.value if hasattr(booking.status, "value") else booking.status,
            "to": new_status.value,
            "at": datetime.now(UTC).isoformat(),
            "by": actor.id,
            "note": note,
        }
    )
    booking.status_history = history


async def create_booking(db: AsyncSession, payload: BookingCreate, user: User) -> Booking:
    turf = await db.get(Turf, payload.turf_id)
    if turf is None:
        raise NotFoundError("Turf not found.")
    if not turf.is_active:
        raise ValidationError("This turf is not currently accepting bookings.")

    start = payload.start_time
    if start.tzinfo is None:
        start = start.replace(tzinfo=UTC)
    start = start.astimezone(UTC)

    if start < datetime.now(UTC) + MIN_LEAD_TIME:
        raise ValidationError("Cannot book a slot in the past.")

    end = payload.end_time
    if end is None:
        end = start + timedelta(minutes=turf.slot_duration_minutes)
    if end.tzinfo is None:
        end = end.replace(tzinfo=UTC)
    end = end.astimezone(UTC)

    if end <= start:
        raise ValidationError("end_time must be after start_time.")
    if end - start > MAX_BOOKING_DURATION:
        raise ValidationError("Bookings cannot exceed 8 hours.")

    # Respect the turf's own availability windows for that weekday.
    if not _within_schedule(turf, start, end):
        raise ValidationError("The requested time is outside this turf's availability hours.")

    # Friendly pre-check; the exclusion constraint is the real guarantee.
    booked = await get_booked_windows(db, turf.id, start, end)
    if any(overlaps(start, end, b_start, b_end) for b_start, b_end in booked):
        raise BookingConflictError(
            "That time slot has just been booked. Please choose another slot."
        )

    booking = Booking(
        turf=turf,  # assign the object, not just the id, so the relationship is
        user=user,  # populated without a lazy load (which cannot await here)
        start_time=start,
        end_time=end,
        status=BookingStatus.CONFIRMED,
        payment_status=PaymentStatus.UNPAID,
        total_price=price_for(turf.price_per_hour, start, end),
        notes=payload.notes,
        status_history=[],
    )
    db.add(booking)
    try:
        await db.flush()
    except IntegrityError as exc:
        # The `no_overlapping_bookings` exclusion constraint fired: another
        # request won the race between our pre-check and this insert.
        await db.rollback()
        raise BookingConflictError(
            "That time slot was just booked by someone else. Please choose another slot."
        ) from exc

    return booking


def _within_schedule(turf: Turf, start: datetime, end: datetime) -> bool:
    """True when [start, end) fits inside an active window for that weekday.

    A turf with no configured schedule is treated as always open, so a turf can
    be created before its weekly hours are defined.
    """
    if not turf.schedules:
        return True

    day_of_week = start.weekday()
    start_time = start.timetz().replace(tzinfo=None)
    end_time = end.timetz().replace(tzinfo=None)

    for schedule in turf.schedules:
        if not schedule.is_active or schedule.day_of_week != day_of_week:
            continue
        if start_time >= schedule.open_time and end_time <= schedule.close_time:
            return True
    return False


async def list_bookings(
    db: AsyncSession,
    *,
    user: User,
    turf_id: int | None = None,
    status: BookingStatus | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Booking], int]:
    stmt = select(Booking).options(selectinload(Booking.turf), selectinload(Booking.user))

    # Non-admins only ever see their own bookings plus bookings on turfs they own.
    if not user.is_admin:
        owned_turf_ids = select(Turf.id).where(Turf.owner_id == user.id)
        stmt = stmt.where((Booking.user_id == user.id) | (Booking.turf_id.in_(owned_turf_ids)))

    if turf_id is not None:
        stmt = stmt.where(Booking.turf_id == turf_id)
    if status is not None:
        stmt = stmt.where(Booking.status == status)
    if date_from is not None:
        stmt = stmt.where(Booking.end_time >= date_from)
    if date_to is not None:
        stmt = stmt.where(Booking.start_time <= date_to)

    total = await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    stmt = stmt.order_by(Booking.start_time.desc()).limit(limit).offset(offset)
    return list(await db.scalars(stmt)), total


async def update_booking(
    db: AsyncSession, booking: Booking, payload: BookingUpdate, actor: User
) -> Booking:
    if not actor.is_admin:
        raise PermissionDeniedError("Only an admin can change a booking's status or payment.")

    data = payload.model_dump(exclude_unset=True)
    new_status = data.get("status")

    if new_status is not None:
        current = BookingStatus(booking.status)
        target = BookingStatus(new_status)
        if target == current:
            pass  # idempotent no-op
        elif target not in ALLOWED_TRANSITIONS[current]:
            raise ValidationError(f"Cannot change a {current.value} booking to {target.value}.")
        else:
            booking.status = target
            _append_history(booking, target, actor, payload.notes)

    if "payment_status" in data and data["payment_status"] is not None:
        payment_status = PaymentStatus(data["payment_status"])
        if payment_status == PaymentStatus.PAID_ON_SITE:
            booking.paid_at = datetime.now(UTC)
        elif payment_status == PaymentStatus.UNPAID:
            booking.paid_at = None
        booking.payment_status = payment_status

    if "notes" in data:
        booking.notes = data["notes"]

    await db.flush()
    return booking


async def cancel_booking(db: AsyncSession, booking: Booking, actor: User) -> Booking:
    """A customer may cancel their own booking; owners/admins may too."""
    assert_can_view(actor, booking)
    if actor.role and actor.role.name == "customer" and booking.user_id != actor.id:
        raise PermissionDeniedError("You can only cancel your own bookings.")

    current = BookingStatus(booking.status)
    if BookingStatus.CANCELLED not in ALLOWED_TRANSITIONS[current]:
        raise ValidationError(f"A {current.value} booking cannot be cancelled.")

    booking.status = BookingStatus.CANCELLED
    _append_history(booking, BookingStatus.CANCELLED, actor, "Cancelled")
    await db.flush()
    return booking
