"""User administration endpoints (admin-scoped)."""

from typing import Annotated

from fastapi import APIRouter, Query, status
from sqlalchemy import select

from app.api.deps import AdminUser, CurrentUser, DbSession, Pagination
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.user import (
    AdminUserCreate,
    PasswordChangeRequest,
    UserRead,
    UserUpdate,
)
from app.services import auth as auth_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead, summary="Current user profile")
async def get_me(user: CurrentUser) -> UserRead:
    return UserRead(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        role=user.role.name if user.role else "customer",
        is_active=user.is_active,
        is_verified=user.is_verified,
    )


@router.patch("/me/password", response_model=MessageResponse, summary="Change own password")
async def change_own_password(
    payload: PasswordChangeRequest, db: DbSession, user: CurrentUser
) -> MessageResponse:
    if not verify_password(payload.current_password, user.hashed_password):
        raise ValidationError("Current password is incorrect.")

    user.hashed_password = hash_password(payload.new_password)
    await db.commit()
    # A password change invalidates every existing session, including this one.
    await auth_service.revoke_all_for_user(db, user.id)
    await db.commit()
    return MessageResponse(message="Password updated. Please sign in again.")


@router.get("", response_model=list[UserRead], summary="List users (admin)")
async def list_users(
    db: DbSession,
    _admin: AdminUser,
    pagination: Pagination,
    search: Annotated[str | None, Query(max_length=120)] = None,
) -> list[UserRead]:
    stmt = select(User)
    if search:
        stmt = stmt.where(User.email.ilike(f"%{search}%"))
    stmt = stmt.order_by(User.id).limit(pagination.limit).offset(pagination.offset)
    users = list(await db.scalars(stmt))
    return [_to_read(u) for u in users]


@router.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a user with any role (admin)",
)
async def create_user(payload: AdminUserCreate, db: DbSession, _admin: AdminUser) -> UserRead:
    """Admin-only provisioning for owner/admin accounts."""
    email = payload.email.lower()
    if await auth_service.get_user_by_email(db, email) is not None:
        raise ConflictError("An account with this email already exists.")

    role = await auth_service.get_role_by_name(db, payload.role)
    user = User(
        email=email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        phone=payload.phone,
        role_id=role.id,
        is_active=True,
        # Accounts created by an admin are trusted; self-registered ones are not.
        is_verified=payload.role != "customer",
    )
    db.add(user)
    await db.flush()
    await db.refresh(user, attribute_names=["role"])
    await db.commit()
    return _to_read(user)


@router.get("/{user_id}", response_model=UserRead, summary="Get a user (admin)")
async def get_user(user_id: int, db: DbSession, _admin: AdminUser) -> UserRead:
    user = await db.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found.")
    return _to_read(user)


@router.patch("/{user_id}", response_model=UserRead, summary="Update a user (admin)")
async def update_user(
    user_id: int, payload: UserUpdate, db: DbSession, admin: AdminUser
) -> UserRead:
    user = await db.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found.")

    data = payload.model_dump(exclude_unset=True)
    new_role = data.pop("role", None)
    is_deactivated = data.get("is_active") is False

    if new_role is not None:
        if user.id == admin.id and new_role != "admin":
            raise ValidationError("You cannot remove your own admin role.")
        role = await auth_service.get_role_by_name(db, new_role)
        user.role_id = role.id

    for field, value in data.items():
        setattr(user, field, value)

    if is_deactivated:
        # Deactivating must not leave live sessions behind.
        await auth_service.revoke_all_for_user(db, user.id)

    await db.flush()
    await db.refresh(user, attribute_names=["role"])
    await db.commit()
    return _to_read(user)


@router.delete("/{user_id}", response_model=MessageResponse, summary="Deactivate a user (admin)")
async def deactivate_user(user_id: int, db: DbSession, admin: AdminUser) -> MessageResponse:
    if user_id == admin.id:
        raise ValidationError("You cannot deactivate your own account.")
    user = await db.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found.")

    user.is_active = False
    await auth_service.revoke_all_for_user(db, user.id)
    await db.commit()
    return MessageResponse(message="User deactivated.")


def _to_read(user: User) -> UserRead:
    return UserRead(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        role=user.role.name if user.role else "customer",
        is_active=user.is_active,
        is_verified=user.is_verified,
    )
