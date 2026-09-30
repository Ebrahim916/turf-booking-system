"""Reusable FastAPI dependencies: authentication and role-based access control."""

from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.common import PaginationParams
from app.services import auth as auth_service

# auto_error=False so a missing header raises our own 401 shape, not FastAPI's.
_bearer = HTTPBearer(auto_error=False, description="JWT access token")

DbSession = Annotated[AsyncSession, Depends(get_db)]
Pagination = Annotated[PaginationParams, Depends()]


def get_client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def get_user_agent(request: Request) -> str | None:
    return request.headers.get("user-agent")


async def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if credentials is None or not credentials.credentials:
        raise AuthenticationError("Not authenticated.")
    return await auth_service.get_user_from_access_token(db, credentials.credentials)


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole) -> Callable[..., Awaitable[User]]:
    """Dependency factory guarding an endpoint behind one or more roles."""

    allowed = set(roles)

    async def _guard(user: CurrentUser) -> User:
        if user.role is None or user.role.name not in {r.value for r in allowed}:
            names = ", ".join(sorted(r.value for r in allowed))
            raise PermissionDeniedError(f"This action requires one of: {names}.")
        return user

    return _guard


AdminUser = Annotated[User, Depends(require_roles(UserRole.ADMIN))]
OwnerOrAdminUser = Annotated[User, Depends(require_roles(UserRole.OWNER, UserRole.ADMIN))]
AuthenticatedUser = Annotated[
    User, Depends(require_roles(UserRole.ADMIN, UserRole.OWNER, UserRole.CUSTOMER))
]
