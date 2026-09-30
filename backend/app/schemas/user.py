"""Authentication and user schemas."""

import re
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.common import ORMModel, TimestampedSchema

# At least one lowercase, one uppercase, one digit, one special character.
PASSWORD_PATTERN = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^\w\s]).{8,128}$")


def _validate_password(value: str) -> str:
    if not PASSWORD_PATTERN.match(value):
        raise ValueError(
            "Password must be at least 8 characters and contain a lowercase "
            "letter, an uppercase letter, a digit, and a symbol."
        )
    return value


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=150)
    phone: str | None = Field(default=None, max_length=20)
    # Self-registration may only create customer accounts. Admin and owner
    # accounts are provisioned by an existing admin, never via public signup.
    role: str = "customer"

    @field_validator("password")
    @classmethod
    def check_password(cls, v: str) -> str:
        return _validate_password(v)

    @field_validator("role")
    @classmethod
    def check_role(cls, v: str) -> str:
        allowed = {"customer"}
        if v not in allowed:
            raise ValueError(f"Role must be one of: {sorted(allowed)}")
        return v

    @field_validator("phone")
    @classmethod
    def check_phone(cls, v: str | None) -> str | None:
        if v is None:
            return None
        cleaned = re.sub(r"[^\d+]", "", v)
        if not re.fullmatch(r"\+?\d{7,15}", cleaned):
            raise ValueError("Phone must be 7-15 digits, optionally starting with '+'.")
        return cleaned

    @field_validator("full_name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip()


class AdminUserCreate(RegisterRequest):
    """Admin-only provisioning. Unlike public signup this may assign any role."""

    role: str = "customer"

    @field_validator("role")
    @classmethod
    def check_role(cls, v: str) -> str:
        allowed = {"admin", "owner", "customer"}
        if v not in allowed:
            raise ValueError(f"Role must be one of: {sorted(allowed)}")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Returned on register, login, and refresh.

    The access token is given in the body for the SPA to hold in memory; the
    refresh token travels in an httpOnly cookie and is never in this payload.
    """

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    expires_at: datetime
    user: "UserRead"


class UserRead(ORMModel):
    id: int
    email: EmailStr
    full_name: str
    phone: str | None
    role: str
    is_active: bool
    is_verified: bool


class UserReadDetailed(TimestampedSchema, UserRead):
    pass


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    phone: str | None = Field(default=None, max_length=20)
    is_active: bool | None = None
    is_verified: bool | None = None
    role: str | None = None

    @field_validator("role")
    @classmethod
    def check_role(cls, v: str | None) -> str | None:
        if v is None:
            return None
        allowed = {"admin", "owner", "customer"}
        if v not in allowed:
            raise ValueError(f"Role must be one of: {sorted(allowed)}")
        return v


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def check_password(cls, v: str) -> str:
        return _validate_password(v)


class SessionRead(ORMModel):
    id: int
    user_agent: str | None
    ip_address: str | None
    created_at: datetime
    last_used_at: datetime | None
    expires_at: datetime
    is_current: bool = False


TokenResponse.model_rebuild()
