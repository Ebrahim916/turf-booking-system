"""v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, bookings, turfs, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(turfs.router)
api_router.include_router(bookings.router)
