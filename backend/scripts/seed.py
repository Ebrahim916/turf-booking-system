"""Development seed data.

Idempotent: safe to run repeatedly. Creates an admin, an owner, a couple of
customers, and some turfs with weekly availability.

Usage:
    python -m scripts.seed          # from the backend/ directory
"""

import asyncio
import os
from datetime import time
from decimal import Decimal

from sqlalchemy import select

from app.core.database import SessionLocal, engine
from app.core.logging import configure_logging, logger
from app.core.security import hash_password
from app.models.role import Role
from app.models.turf import Turf, TurfSchedule
from app.models.user import User

# Seeded turfs are bookable 08:00-22:00 on the days each one lists.
OPEN_TIME = time(8, 0)
CLOSE_TIME = time(22, 0)
WEEKDAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


async def _ensure_role(db, name: str, description: str) -> Role:
    role = await db.scalar(select(Role).where(Role.name == name))
    if role is None:
        role = Role(name=name, description=description)
        db.add(role)
        await db.flush()
        logger.info("role created", role=name)
    return role


async def _ensure_user(
    db, *, email: str, password: str, full_name: str, role: Role, phone: str | None = None
) -> User:
    user = await db.scalar(select(User).where(User.email == email))
    if user is not None:
        return user
    user = User(
        email=email,
        hashed_password=hash_password(password),
        full_name=full_name,
        phone=phone,
        role_id=role.id,
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    await db.flush()
    logger.info("user created", email=email, role=role.name)
    return user


async def _ensure_turf(
    db,
    *,
    owner: User,
    name: str,
    address: str,
    city: str,
    size: str,
    surface: str,
    price_per_hour: str,
    days: list[int],
) -> Turf:
    turf = await db.scalar(select(Turf).where(Turf.name == name))
    if turf is not None:
        return turf
    turf = Turf(
        name=name,
        description=f"{size} {surface} pitch available for hourly booking.",
        address=address,
        city=city,
        size=size,
        surface=surface,
        price_per_hour=Decimal(price_per_hour),
        slot_duration_minutes=60,
        owner_id=owner.id,
        is_active=True,
    )
    db.add(turf)
    await db.flush()

    for day in days:
        db.add(
            TurfSchedule(
                turf_id=turf.id,
                day_of_week=day,
                open_time=OPEN_TIME,
                close_time=CLOSE_TIME,
                is_active=True,
            )
        )
    await db.flush()
    logger.info("turf created", name=name, days=[WEEKDAY_NAMES[d] for d in days])
    return turf


async def main() -> None:
    configure_logging()
    try:
        await _seed()
    finally:
        # Dispose inside the same event loop that created the pool; creating a
        # second loop for disposal raises inside asyncpg's close path.
        await engine.dispose()


async def _seed() -> None:

    async with SessionLocal() as db:
        admin_role = await _ensure_role(db, name="admin", description="Full access.")
        owner_role = await _ensure_role(db, name="owner", description="Manages own turfs.")
        customer_role = await _ensure_role(db, name="customer", description="Books slots.")

        admin = await _ensure_user(
            db,
            email=os.getenv("SEED_ADMIN_EMAIL", "admin@example.com"),
            password=os.getenv("SEED_ADMIN_PASSWORD", "Admin@12345"),
            full_name="System Administrator",
            role=admin_role,
        )
        owner = await _ensure_user(
            db,
            email="owner@example.com",
            password="Owner@12345",
            full_name="Ravi Owner",
            role=owner_role,
            phone="+919800000001",
        )
        await _ensure_user(
            db,
            email="customer@example.com",
            password="Customer@12345",
            full_name="Anita Customer",
            role=customer_role,
            phone="+919800000002",
        )

        await _ensure_turf(
            db,
            owner=owner,
            name="Green Park Arena",
            address="12 Sports Complex Road",
            city="Bengaluru",
            size="5-a-side",
            surface="artificial",
            price_per_hour="800.00",
            days=[0, 1, 2, 3, 4, 5, 6],
        )
        await _ensure_turf(
            db,
            owner=owner,
            name="Sunrise Football Ground",
            address="45 Lake View Road",
            city="Bengaluru",
            size="7-a-side",
            surface="natural grass",
            price_per_hour="1500.00",
            days=[0, 1, 2, 3, 4, 5],
        )
        await _ensure_turf(
            db,
            owner=admin,
            name="City Badminton Court",
            address="7 Recreation Street",
            city="Hyderabad",
            size="2-court",
            surface="wooden",
            price_per_hour="500.00",
            days=[0, 1, 2, 3, 4, 5, 6],
        )

        await db.commit()
        logger.info("seed complete", admin_email=admin.email)


if __name__ == "__main__":
    asyncio.run(main())
