"""Turf and schedule endpoints."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Query, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession, OwnerOrAdminUser, Pagination
from app.core.exceptions import NotFoundError, PermissionDeniedError, ValidationError
from app.models.enums import UserRole
from app.models.turf import TurfSchedule
from app.schemas.common import MessageResponse
from app.schemas.turf import (
    ScheduleCreate,
    ScheduleRead,
    ScheduleUpdate,
    SlotRead,
    TurfCreate,
    TurfRead,
    TurfUpdate,
)
from app.services import slot as slot_service
from app.services import turf as turf_service

router = APIRouter(prefix="/turfs", tags=["turfs"])


@router.get("", response_model=list[TurfRead], summary="List bookable turfs")
async def list_turfs(
    db: DbSession,
    pagination: Pagination,
    _user: CurrentUser,
    city: Annotated[str | None, Query(max_length=100)] = None,
) -> list[TurfRead]:
    turfs, _total = await turf_service.list_turfs(
        db, city=city, limit=pagination.limit, offset=pagination.offset
    )
    return [TurfRead.model_validate(t) for t in turfs]


@router.post(
    "",
    response_model=TurfRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a turf (owner or admin)",
)
async def create_turf(payload: TurfCreate, db: DbSession, user: OwnerOrAdminUser) -> TurfRead:
    turf = await turf_service.create_turf(db, payload, user)
    await db.commit()
    return await _reload(db, turf.id)


@router.get("/{turf_id}", response_model=TurfRead, summary="Get a turf")
async def get_turf(turf_id: int, db: DbSession, _user: CurrentUser) -> TurfRead:
    turf = await turf_service.get_turf(db, turf_id)
    return TurfRead.model_validate(turf)


@router.patch("/{turf_id}", response_model=TurfRead, summary="Update a turf (owner or admin)")
async def update_turf(
    turf_id: int, payload: TurfUpdate, db: DbSession, user: OwnerOrAdminUser
) -> TurfRead:
    turf = await turf_service.get_turf(db, turf_id)
    turf_service.assert_can_manage(user, turf)
    await turf_service.update_turf(db, turf, payload)
    await db.commit()
    return await _reload(db, turf.id)


@router.delete(
    "/{turf_id}", response_model=MessageResponse, summary="Deactivate a turf (owner or admin)"
)
async def delete_turf(turf_id: int, db: DbSession, user: OwnerOrAdminUser) -> MessageResponse:
    turf = await turf_service.get_turf(db, turf_id)
    turf_service.assert_can_manage(user, turf)
    await turf_service.delete_turf(db, turf)
    await db.commit()
    return MessageResponse(message="Turf deactivated.")


# --- Availability ---


@router.get(
    "/{turf_id}/availability",
    response_model=list[SlotRead],
    summary="Bookable slots for a date",
)
async def get_availability(
    turf_id: int,
    db: DbSession,
    _user: CurrentUser,
    date: Annotated[str, Query(description="Calendar date, YYYY-MM-DD (UTC)")],
) -> list[SlotRead]:
    try:
        on_date = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=UTC)
    except ValueError as exc:
        raise ValidationError("date must be formatted as YYYY-MM-DD.") from exc

    turf = await turf_service.get_turf(db, turf_id)
    return await slot_service.generate_slots(db, turf, on_date)


# --- Schedules ---


@router.get(
    "/{turf_id}/schedules", response_model=list[ScheduleRead], summary="List weekly availability"
)
async def list_schedules(turf_id: int, db: DbSession, user: OwnerOrAdminUser) -> list[ScheduleRead]:
    turf = await turf_service.get_turf(db, turf_id)
    turf_service.assert_can_manage(user, turf)
    return [ScheduleRead.model_validate(s) for s in turf.schedules]


@router.post(
    "/{turf_id}/schedules",
    response_model=ScheduleRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a weekly availability window (owner or admin)",
)
async def add_schedule(
    turf_id: int, payload: ScheduleCreate, db: DbSession, user: OwnerOrAdminUser
) -> ScheduleRead:
    turf = await turf_service.get_turf(db, turf_id)
    turf_service.assert_can_manage(user, turf)
    schedule = await turf_service.add_schedule(db, turf, payload)
    await db.commit()
    return ScheduleRead.model_validate(schedule)


@router.patch(
    "/{turf_id}/schedules/{schedule_id}",
    response_model=ScheduleRead,
    summary="Update an availability window (owner or admin)",
)
async def update_schedule(
    turf_id: int,
    schedule_id: int,
    payload: ScheduleUpdate,
    db: DbSession,
    user: OwnerOrAdminUser,
) -> ScheduleRead:
    turf = await turf_service.get_turf(db, turf_id)
    turf_service.assert_can_manage(user, turf)
    schedule = await _get_schedule(db, turf_id, schedule_id)
    schedule = await turf_service.update_schedule(db, schedule, payload)
    await db.commit()
    return ScheduleRead.model_validate(schedule)


@router.delete(
    "/{turf_id}/schedules/{schedule_id}",
    response_model=MessageResponse,
    summary="Remove an availability window (owner or admin)",
)
async def delete_schedule(
    turf_id: int, schedule_id: int, db: DbSession, user: OwnerOrAdminUser
) -> MessageResponse:
    turf = await turf_service.get_turf(db, turf_id)
    turf_service.assert_can_manage(user, turf)
    schedule = await _get_schedule(db, turf_id, schedule_id)
    await turf_service.delete_schedule(db, schedule)
    await db.commit()
    return MessageResponse(message="Schedule removed.")


@router.get("/mine/all", response_model=list[TurfRead], summary="Turfs owned by the caller")
async def list_my_turfs(db: DbSession, user: CurrentUser, pagination: Pagination) -> list[TurfRead]:
    if user.role and user.role.name == UserRole.CUSTOMER.value:
        raise PermissionDeniedError("Customers do not own turfs.")
    turfs, _ = await turf_service.list_turfs(
        db,
        owner_id=user.id,
        include_inactive=True,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [TurfRead.model_validate(t) for t in turfs]


async def _get_schedule(db: DbSession, turf_id: int, schedule_id: int) -> TurfSchedule:
    schedule = await db.scalar(
        select(TurfSchedule).where(TurfSchedule.id == schedule_id, TurfSchedule.turf_id == turf_id)
    )
    if schedule is None:
        raise NotFoundError("Schedule not found.")
    return schedule


async def _reload(db: DbSession, turf_id: int) -> TurfRead:
    return TurfRead.model_validate(await turf_service.get_turf(db, turf_id))
