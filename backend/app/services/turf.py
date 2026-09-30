"""Turf and schedule management."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError, ValidationError
from app.models.turf import Turf, TurfSchedule
from app.models.user import User
from app.schemas.turf import ScheduleCreate, ScheduleUpdate, TurfCreate, TurfUpdate


async def get_turf(db: AsyncSession, turf_id: int, *, with_schedules: bool = True) -> Turf:
    stmt = select(Turf).where(Turf.id == turf_id)
    if with_schedules:
        stmt = stmt.options(selectinload(Turf.schedules))
    turf = await db.scalar(stmt)
    if turf is None:
        raise NotFoundError("Turf not found.")
    return turf


def assert_can_manage(user: User, turf: Turf) -> None:
    """Owners manage only their own turfs; admins manage any turf."""
    if user.is_admin:
        return
    if turf.owner_id != user.id:
        raise PermissionDeniedError("You do not have access to this turf.")


async def list_turfs(
    db: AsyncSession,
    *,
    owner_id: int | None = None,
    city: str | None = None,
    include_inactive: bool = False,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Turf], int]:
    stmt = select(Turf).options(selectinload(Turf.schedules))
    if owner_id is not None:
        stmt = stmt.where(Turf.owner_id == owner_id)
    if city:
        stmt = stmt.where(Turf.city.ilike(f"%{city}%"))
    if not include_inactive:
        stmt = stmt.where(Turf.is_active.is_(True))

    total = await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    stmt = stmt.order_by(Turf.name).limit(limit).offset(offset)
    return list(await db.scalars(stmt)), total


async def create_turf(db: AsyncSession, payload: TurfCreate, owner: User) -> Turf:
    turf = Turf(**payload.model_dump(), owner_id=owner.id, is_active=True)
    db.add(turf)
    await db.flush()
    return turf


async def update_turf(db: AsyncSession, turf: Turf, payload: TurfUpdate) -> Turf:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(turf, field, value)
    await db.flush()
    return turf


async def delete_turf(db: AsyncSession, turf: Turf) -> None:
    """Soft delete: historical bookings must keep referencing the turf."""
    turf.is_active = False
    await db.flush()


async def add_schedule(db: AsyncSession, turf: Turf, payload: ScheduleCreate) -> TurfSchedule:
    existing = await db.scalar(
        select(TurfSchedule).where(
            TurfSchedule.turf_id == turf.id, TurfSchedule.day_of_week == payload.day_of_week
        )
    )
    if existing is not None:
        raise ConflictError(
            f"A schedule already exists for this turf on day {payload.day_of_week}. "
            "Update it instead."
        )

    schedule = TurfSchedule(turf_id=turf.id, **payload.model_dump())
    db.add(schedule)
    try:
        await db.flush()
    except Exception as exc:  # pragma: no cover - relies on DB exclusion constraint
        await db.rollback()
        raise ConflictError(
            "This availability window overlaps an existing one for the same day."
        ) from exc
    return schedule


async def update_schedule(
    db: AsyncSession, schedule: TurfSchedule, payload: ScheduleUpdate
) -> TurfSchedule:
    data = payload.model_dump(exclude_unset=True)
    # Validate the supplied bound against the stored value for the other one.
    only_open = "open_time" in data and "close_time" not in data
    only_close = "close_time" in data and "open_time" not in data
    if only_open and data["open_time"] >= schedule.close_time:
        raise ValidationError("open_time must be earlier than close_time.")
    if only_close and schedule.open_time >= data["close_time"]:
        raise ValidationError("open_time must be earlier than close_time.")

    for field, value in data.items():
        setattr(schedule, field, value)
    await db.flush()
    return schedule


async def delete_schedule(db: AsyncSession, schedule: TurfSchedule) -> None:
    await db.delete(schedule)
    await db.flush()
