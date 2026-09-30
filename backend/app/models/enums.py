"""Enumerations shared across models, schemas, and services.

These deliberately use `str, Enum` rather than `StrEnum`: they are persisted as
VARCHAR and compared against plain strings, and the mixin keeps `==` and
SQLAlchemy's string binding working naturally.
"""

import enum


class UserRole(str, enum.Enum):
    """Roles are seeded into the `roles` table and referenced by name."""

    ADMIN = "admin"
    OWNER = "owner"
    CUSTOMER = "customer"


class BookingStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"

    @property
    def occupies_slot(self) -> bool:
        """Whether a booking in this state should block the time slot.

        Mirrors the WHERE clause of the `no_overlapping_bookings` exclusion
        constraint, which is the real authority on this.
        """
        return self in (BookingStatus.PENDING, BookingStatus.CONFIRMED)


class PaymentStatus(str, enum.Enum):
    """Cash on site only for v1; online capture arrives with a payment adapter."""

    UNPAID = "unpaid"
    PAID_ON_SITE = "paid_on_site"
    REFUNDED = "refunded"
