"""Domain exceptions that map cleanly onto HTTP responses."""

from typing import Any


class AppError(Exception):
    """Base class for expected, user-facing application errors."""

    status_code: int = 400
    code: str = "app_error"

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        status_code: int | None = None,
        details: Any | None = None,
    ) -> None:
        self.message = message or self.__class__.__doc__ or "An error occurred."
        self.code = code or self.code
        self.status_code = status_code or self.status_code
        self.details = details
        super().__init__(self.message)


class NotFoundError(AppError):
    """The requested resource does not exist."""

    status_code = 404
    code = "not_found"


class ConflictError(AppError):
    """The request conflicts with the current state of the resource."""

    status_code = 409
    code = "conflict"


class ValidationError(AppError):
    """The request was well-formed but semantically invalid."""

    status_code = 422
    code = "validation_error"


class AuthenticationError(AppError):
    """Authentication credentials are missing or invalid."""

    status_code = 401
    code = "authentication_error"


class PermissionDeniedError(AppError):
    """The authenticated user is not allowed to perform this action."""

    status_code = 403
    code = "permission_denied"


class BookingConflictError(ConflictError):
    """The requested time slot overlaps an existing booking."""

    code = "booking_conflict"
