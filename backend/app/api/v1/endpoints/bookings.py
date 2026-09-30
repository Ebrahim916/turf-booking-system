"""Booking endpoints."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import AdminUser, CurrentUser, DbSession, Pagination
from app.models.booking import Booking
from app.models.enums import BookingStatus
from app.schemas.booking import BookingCreate, BookingRead, BookingUpdate
from app.schemas.common import MessageResponse
from app.services import booking as booking_service

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post(
    "",
    response_model=BookingRead,
    status_code=status.HTTP_201_CREATED,
    summary="Book a turf slot",
)
async def create_booking(payload: BookingCreate, db: DbSession, user: CurrentUser) -> BookingRead:
    booking = await booking_service.create_booking(db, payload, user)
    await db.commit()
    return _to_read(booking)


@router.get("", response_model=list[BookingRead], summary="List bookings")
async def list_bookings(
    db: DbSession,
    user: CurrentUser,
    pagination: Pagination,
    turf_id: Annotated[int | None, Query(ge=1)] = None,
    booking_status: Annotated[BookingStatus | None, Query(alias="status")] = None,
    date_from: Annotated[datetime | None, Query()] = None,
    date_to: Annotated[datetime | None, Query()] = None,
) -> list[BookingRead]:
    bookings, _total = await booking_service.list_bookings(
        db,
        user=user,
        turf_id=turf_id,
        status=booking_status,
        date_from=date_from,
        date_to=date_to,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [_to_read(b) for b in bookings]


@router.get("/{booking_id}", response_model=BookingRead, summary="Get a booking")
async def get_booking(booking_id: int, db: DbSession, user: CurrentUser) -> BookingRead:
    booking = await booking_service.get_booking(db, booking_id)
    booking_service.assert_can_view(user, booking)
    return _to_read(booking)


@router.post(
    "/{booking_id}/cancel",
    response_model=BookingRead,
    summary="Cancel a booking",
)
async def cancel_booking(booking_id: int, db: DbSession, user: CurrentUser) -> BookingRead:
    booking = await booking_service.get_booking(db, booking_id)
    booking = await booking_service.cancel_booking(db, booking, user)
    await db.commit()
    return _to_read(booking)


@router.patch(
    "/{booking_id}",
    response_model=BookingRead,
    summary="Update booking status or mark payment received (admin)",
)
async def update_booking(
    booking_id: int, payload: BookingUpdate, db: DbSession, admin: AdminUser
) -> BookingRead:
    booking = await booking_service.get_booking(db, booking_id)
    booking = await booking_service.update_booking(db, booking, payload, admin)
    await db.commit()
    return _to_read(booking)


@router.delete("/{booking_id}", response_model=MessageResponse, summary="Cancel a booking (admin)")
async def admin_cancel_booking(booking_id: int, db: DbSession, admin: AdminUser) -> MessageResponse:
    booking = await booking_service.get_booking(db, booking_id)
    await booking_service.cancel_booking(db, booking, admin)
    await db.commit()
    return MessageResponse(message="Booking cancelled.")


def _to_read(booking: Booking) -> BookingRead:
    return BookingRead(
        id=booking.id,
        turf_id=booking.turf_id,
        turf_name=booking.turf.name if booking.turf else None,
        user_id=booking.user_id,
        user_name=booking.user.full_name if booking.user else None,
        start_time=booking.start_time,
        end_time=booking.end_time,
        status=booking.status,
        payment_status=booking.payment_status,
        total_price=booking.total_price,
        notes=booking.notes,
    )
