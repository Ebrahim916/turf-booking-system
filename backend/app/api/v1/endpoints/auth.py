"""Authentication endpoints."""

from fastapi import APIRouter, Request, Response, status

from app.api.deps import CurrentUser, DbSession, get_client_ip, get_user_agent
from app.core.config import settings
from app.core.exceptions import AuthenticationError
from app.schemas.common import MessageResponse
from app.schemas.user import LoginRequest, RegisterRequest, TokenResponse, UserRead
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

# Scoping the cookie to the auth prefix means it is not attached to every
# request to the API, which narrows its exposure surface.
REFRESH_COOKIE_PATH = "/api/v1/auth"


def _set_refresh_cookie(response: Response, raw_token: str) -> None:
    response.set_cookie(
        key=settings.refresh_token_cookie_name,
        value=raw_token,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        httponly=True,  # unreachable from JavaScript, so XSS cannot exfiltrate it
        secure=settings.refresh_token_cookie_secure or settings.is_production,
        samesite=settings.refresh_token_cookie_samesite,
        path=REFRESH_COOKIE_PATH,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.refresh_token_cookie_name,
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        secure=settings.refresh_token_cookie_secure or settings.is_production,
        samesite=settings.refresh_token_cookie_samesite,
    )


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a customer account",
)
async def register(
    payload: RegisterRequest, response: Response, request: Request, db: DbSession
) -> TokenResponse:
    issued = await auth_service.register(
        db,
        payload,
        user_agent=get_user_agent(request),
        ip_address=get_client_ip(request),
    )
    _set_refresh_cookie(response, issued.refresh_token)
    return issued.tokens


@router.post("/login", response_model=TokenResponse, summary="Exchange credentials for tokens")
async def login(
    payload: LoginRequest, response: Response, request: Request, db: DbSession
) -> TokenResponse:
    issued = await auth_service.login(
        db,
        payload,
        user_agent=get_user_agent(request),
        ip_address=get_client_ip(request),
    )
    _set_refresh_cookie(response, issued.refresh_token)
    return issued.tokens


@router.post("/refresh", response_model=TokenResponse, summary="Rotate the refresh token")
async def refresh(request: Request, response: Response, db: DbSession) -> TokenResponse:
    raw_token = request.cookies.get(settings.refresh_token_cookie_name)
    if not raw_token:
        raise AuthenticationError("No refresh token cookie was sent.")
    issued = await auth_service.rotate_refresh_token(
        db,
        raw_token,
        user_agent=get_user_agent(request),
        ip_address=get_client_ip(request),
    )
    _set_refresh_cookie(response, issued.refresh_token)
    return issued.tokens


@router.post("/logout", response_model=MessageResponse, summary="Revoke the current session")
async def logout(request: Request, response: Response, db: DbSession) -> MessageResponse:
    raw_token = request.cookies.get(settings.refresh_token_cookie_name)
    if raw_token:
        await auth_service.logout(db, raw_token)
    _clear_refresh_cookie(response)
    return MessageResponse(message="Logged out.")


@router.post(
    "/logout-all",
    response_model=MessageResponse,
    summary="Revoke every session for the current user",
)
async def logout_all(response: Response, db: DbSession, user: CurrentUser) -> MessageResponse:
    revoked = await auth_service.logout_all(db, user)
    _clear_refresh_cookie(response)
    return MessageResponse(message=f"Revoked {revoked} session(s).")


@router.get("/me", response_model=UserRead, summary="Current user profile")
async def me(user: CurrentUser) -> UserRead:
    return UserRead(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        role=user.role.name if user.role else "customer",
        is_active=user.is_active,
        is_verified=user.is_verified,
    )
