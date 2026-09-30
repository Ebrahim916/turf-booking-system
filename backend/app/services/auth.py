"""Authentication service: registration, login, and refresh-token rotation."""

from datetime import UTC, datetime
from typing import NamedTuple

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_refresh_token,
    refresh_token_expiry,
    verify_password,
)
from app.models.enums import UserRole
from app.models.role import Role
from app.models.user import RefreshToken, User
from app.schemas.user import LoginRequest, RegisterRequest, TokenResponse, UserRead

# Access tokens are short-lived and stateless, so a leaked one stays valid for at
# most this long. Only the refresh token is server-side revocable.
ACCESS_TOKEN_LIFETIME_SECONDS = settings.access_token_expire_minutes * 60


class IssuedTokens(NamedTuple):
    """A freshly minted token pair.

    `refresh_token` is the raw value, returned to the API layer only so it can be
    written to an httpOnly cookie. It is never persisted and never serialised
    into a response body.
    """

    tokens: TokenResponse
    refresh_token: str


async def get_role_by_name(db: AsyncSession, name: str) -> Role:
    role = await db.scalar(select(Role).where(Role.name == name))
    if role is None:
        raise NotFoundError(f"Role '{name}' is not seeded.")
    return role


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    return await db.scalar(select(User).where(User.email == email.lower()))


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    return await db.get(User, user_id)


async def _persist_refresh_token(
    db: AsyncSession,
    user: User,
    raw_token: str,
    *,
    user_agent: str | None,
    ip_address: str | None,
    replaced_by_id: int | None = None,
) -> RefreshToken:
    record = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(raw_token),
        expires_at=refresh_token_expiry(),
        user_agent=(user_agent or "")[:255] or None,
        ip_address=(ip_address or "")[:45] or None,
        replaced_by_id=replaced_by_id,
    )
    db.add(record)
    return record


async def _issue_token_pair(
    db: AsyncSession,
    user: User,
    *,
    user_agent: str | None,
    ip_address: str | None,
    replaced_by_id: int | None = None,
) -> IssuedTokens:
    raw_refresh, _ = create_refresh_token()
    refresh_record = await _persist_refresh_token(
        db,
        user,
        raw_refresh,
        user_agent=user_agent,
        ip_address=ip_address,
        replaced_by_id=replaced_by_id,
    )
    await db.flush()

    access_token, expires_at = create_access_token(
        str(user.id),
        role=user.role.name if user.role else None,
        session_id=str(refresh_record.id),
    )
    return IssuedTokens(
        tokens=TokenResponse(
            access_token=access_token,
            expires_in=ACCESS_TOKEN_LIFETIME_SECONDS,
            expires_at=expires_at,
            user=_to_user_read(user),
        ),
        refresh_token=raw_refresh,
    )


def _to_user_read(user: User) -> UserRead:
    return UserRead(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        role=user.role.name if user.role else UserRole.CUSTOMER.value,
        is_active=user.is_active,
        is_verified=user.is_verified,
    )


async def register(
    db: AsyncSession,
    payload: RegisterRequest,
    *,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> IssuedTokens:
    email = payload.email.lower()
    if await get_user_by_email(db, email) is not None:
        raise ConflictError("An account with this email already exists.")

    role = await get_role_by_name(db, payload.role)
    user = User(
        email=email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        phone=payload.phone,
        role_id=role.id,
        is_active=True,
        is_verified=False,
    )
    db.add(user)
    try:
        await db.flush()
    except IntegrityError as exc:
        # Lost a race against a concurrent signup for the same email.
        await db.rollback()
        raise ConflictError("An account with this email already exists.") from exc

    await db.refresh(user, attribute_names=["role"])
    issued = await _issue_token_pair(db, user, user_agent=user_agent, ip_address=ip_address)
    await db.commit()
    return issued


async def login(
    db: AsyncSession,
    payload: LoginRequest,
    *,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> IssuedTokens:
    user = await get_user_by_email(db, payload.email.lower())
    # Always run a verification so a missing account and a wrong password take
    # comparable time, avoiding an email-enumeration timing oracle.
    stored_hash = user.hashed_password if user else "$argon2id$v=19$m=65536,t=3,p=4$aaaa$aaaa"
    password_ok = verify_password(payload.password, stored_hash)

    if user is None or not password_ok:
        raise AuthenticationError("Incorrect email or password.")
    if not user.is_active:
        raise PermissionDeniedError("This account has been deactivated.")

    issued = await _issue_token_pair(db, user, user_agent=user_agent, ip_address=ip_address)
    await db.commit()
    return issued


async def _revoke_family(db: AsyncSession, record: RefreshToken) -> None:
    """Revoke a refresh-token chain. Used on logout and on reuse detection."""
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == record.user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )


async def rotate_refresh_token(
    db: AsyncSession,
    raw_token: str,
    *,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> IssuedTokens:
    """Exchange a valid refresh token for a new pair, rotating the old record.

    Presenting an already-revoked token is treated as theft: the entire family
    for that user is revoked and the caller must log in again.
    """
    token_hash = hash_refresh_token(raw_token)
    record = await db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))

    if record is None:
        raise AuthenticationError("Invalid refresh token.")

    if record.revoked_at is not None:
        await _revoke_family(db, record)
        await db.commit()
        raise AuthenticationError("Refresh token has been revoked. Please sign in again.")

    if record.expires_at <= datetime.now(UTC):
        raise AuthenticationError("Refresh token has expired. Please sign in again.")

    user = await db.get(User, record.user_id)
    if user is None or not user.is_active:
        raise AuthenticationError("Account is no longer active.")

    record.revoked_at = datetime.now(UTC)
    record.last_used_at = datetime.now(UTC)
    await db.flush()

    new_raw_refresh, _ = create_refresh_token()
    new_record = await _persist_refresh_token(
        db, user, new_raw_refresh, user_agent=user_agent, ip_address=ip_address
    )
    await db.flush()
    record.replaced_by_id = new_record.id

    access_token, expires_at = create_access_token(
        str(user.id),
        role=user.role.name if user.role else None,
        session_id=str(new_record.id),
    )
    await db.commit()

    return IssuedTokens(
        tokens=TokenResponse(
            access_token=access_token,
            expires_in=ACCESS_TOKEN_LIFETIME_SECONDS,
            expires_at=expires_at,
            user=_to_user_read(user),
        ),
        refresh_token=new_raw_refresh,
    )


async def logout(db: AsyncSession, raw_token: str) -> None:
    token_hash = hash_refresh_token(raw_token)
    record = await db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    if record is None:
        # Idempotent: logging out an unknown token is not an error.
        return
    record.revoked_at = datetime.now(UTC)
    await db.commit()


async def logout_all(db: AsyncSession, user: User) -> int:
    """Revoke every active session for a user. Returns how many were revoked."""
    result = await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
    await db.commit()
    # An UPDATE through AsyncSession.execute returns a CursorResult at runtime,
    # but the declared Result type does not expose rowcount.
    return int(getattr(result, "rowcount", 0) or 0)


async def revoke_all_for_user(db: AsyncSession, user_id: int) -> None:
    """Called when a password changes or an admin deactivates an account."""
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )


async def get_user_from_access_token(db: AsyncSession, token: str) -> User:
    payload = decode_token(token, expected_type="access")
    user_id = payload.get("sub")
    try:
        user = await db.get(User, int(user_id))  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise AuthenticationError("Malformed token subject.") from exc

    if user is None:
        raise AuthenticationError("User no longer exists.")
    if not user.is_active:
        raise PermissionDeniedError("This account has been deactivated.")
    return user
