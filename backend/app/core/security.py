"""Password hashing, JWT issuing/verification, and refresh-token helpers."""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from jose import JWTError, jwt
from pwdlib import PasswordHash

from app.core.config import settings

# Argon2id via pwdlib. `bcrypt` is retained as a verify-only backend so that
# hashes created by an earlier iteration of the schema still validate.
_password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _password_hash.verify(password, password_hash)


TokenType = Literal["access", "refresh"]


def _create_token(
    subject: str,
    token_type: TokenType,
    expires_delta: timedelta,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "jti": uuid.uuid4().hex,
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(
    subject: str, *, role: str | None = None, session_id: str | None = None
) -> tuple[str, datetime]:
    """Return an access token and its expiry. The `jti` doubles as the session id."""
    expires = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    extra: dict[str, Any] = {}
    if role:
        extra["role"] = role
    if session_id:
        extra["sid"] = session_id
    return (
        _create_token(
            subject,
            "access",
            timedelta(minutes=settings.access_token_expire_minutes),
            extra,
        ),
        expires,
    )


def create_refresh_token() -> tuple[str, datetime]:
    """Return a cryptographically random opaque refresh token and its expiry."""
    return secrets.token_urlsafe(48), refresh_token_expiry()


def refresh_token_expiry() -> datetime:
    return datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)


def decode_token(token: str, expected_type: TokenType | None = None) -> dict[str, Any]:
    """Decode and validate a JWT. Raises AuthenticationError when invalid."""
    from app.core.exceptions import AuthenticationError

    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise AuthenticationError("Invalid or expired token.") from exc

    if expected_type is not None and payload.get("type") != expected_type:
        raise AuthenticationError("Invalid token type.")
    if not payload.get("sub"):
        raise AuthenticationError("Token is missing a subject.")
    return payload


def hash_refresh_token(raw_token: str) -> str:
    """Hash a refresh token for storage. The raw token is never persisted.

    SHA-256 is appropriate here (unlike passwords) because refresh tokens are
    384 bits of CSPRNG output, so they carry no low-entropy guessing risk.
    """
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
