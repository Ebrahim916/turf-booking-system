"""Shared pytest fixtures.

Integration tests run against a dedicated database so a test run can never touch
development data. Set TEST_DATABASE_URL to override the default.
"""

import os
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault("ENVIRONMENT", "test")
# Point at a test-only database before importing anything that builds the engine.
os.environ.setdefault(
    "DATABASE_URL",
    os.getenv(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://turf:turf@localhost:5433/turf_booking_test",
    ),
)

from app.core.security import hash_password
from app.models import Base
from app.models.enums import UserRole
from app.models.role import Role
from app.models.turf import Turf, TurfSchedule
from app.models.user import User

TEST_DB_URL = os.environ["DATABASE_URL"]

ROLE_DESCRIPTIONS = {
    "admin": "Full access.",
    "owner": "Manages own turfs.",
    "customer": "Books slots.",
}

DEFAULT_PASSWORD = "Test@12345"


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest_asyncio.fixture
async def engine():
    """A fresh schema per test, dropped afterwards."""
    test_engine = create_async_engine(TEST_DB_URL, echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(_create_schema)
    try:
        yield test_engine
    finally:
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await test_engine.dispose()


def _create_schema(connection) -> None:
    """Create the schema plus the constraints that only the migration can add.

    Sync, because `Connection.run_sync` passes a sync connection. The exclusion
    constraints are the real double-booking guarantee, so tests must exercise
    them rather than relying only on the application pre-check.
    """
    Base.metadata.create_all(connection)
    connection.execute(text("CREATE EXTENSION IF NOT EXISTS btree_gist"))
    connection.execute(
        text(
            """
            ALTER TABLE bookings
            ADD CONSTRAINT no_overlapping_bookings
            EXCLUDE USING gist (
                turf_id WITH =,
                tstzrange(start_time, end_time) WITH &&
            ) WHERE (status IN ('pending', 'confirmed'))
            """
        )
    )
    connection.execute(
        text(
            """
            ALTER TABLE turf_schedules
            ADD CONSTRAINT no_overlapping_schedules
            EXCLUDE USING gist (
                turf_id WITH =,
                day_of_week WITH =,
                int8range(
                    (EXTRACT(HOUR FROM open_time) * 3600
                     + EXTRACT(MINUTE FROM open_time) * 60)::bigint,
                    (EXTRACT(HOUR FROM close_time) * 3600
                     + EXTRACT(MINUTE FROM close_time) * 60)::bigint
                ) WITH &&
            )
            """
        )
    )


@pytest_asyncio.fixture
async def db(engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def seeded(db: AsyncSession) -> dict[str, object]:
    """Create the three roles plus one user per role."""
    roles: dict[str, Role] = {}
    for name, description in ROLE_DESCRIPTIONS.items():
        role = Role(name=name, description=description)
        db.add(role)
        roles[name] = role
    await db.flush()

    users: dict[str, User] = {}
    for role_name, email in (
        ("admin", "admin@example.com"),
        ("owner", "owner@example.com"),
        ("customer", "customer@example.com"),
    ):
        user = User(
            email=email,
            hashed_password=hash_password(DEFAULT_PASSWORD),
            full_name=f"Test {role_name.title()}",
            role_id=roles[role_name].id,
            is_active=True,
            is_verified=True,
        )
        db.add(user)
        users[role_name] = user
    await db.commit()
    return {"roles": roles, "users": users, "password": DEFAULT_PASSWORD}


@pytest_asyncio.fixture
async def turf(db: AsyncSession, seeded) -> Turf:
    """A turf open 08:00-22:00 every day, owned by the owner user."""
    owner: User = seeded["users"]["owner"]  # type: ignore[index]
    new_turf = Turf(
        name="Test Arena",
        description="Test pitch",
        address="1 Test Street",
        city="Testville",
        size="5-a-side",
        surface="artificial",
        price_per_hour=Decimal("100.00"),
        slot_duration_minutes=60,
        owner_id=owner.id,
        is_active=True,
    )
    db.add(new_turf)
    await db.flush()
    for day in range(7):
        db.add(
            TurfSchedule(
                turf_id=new_turf.id,
                day_of_week=day,
                open_time=time(8, 0),
                close_time=time(22, 0),
                is_active=True,
            )
        )
    await db.commit()
    return new_turf


@pytest_asyncio.fixture
async def tomorrow() -> datetime:
    """A UTC datetime one day out at 10:00 - safely inside the seeded window."""
    return (datetime.now(UTC) + timedelta(days=1)).replace(
        hour=10, minute=0, second=0, microsecond=0
    )


@pytest_asyncio.fixture
async def client(engine) -> AsyncGenerator[AsyncClient, None]:
    """An ASGI client whose requests use the test session.

    `get_db` is overridden to the test session factory, so the API handlers and
    the test observe the same transaction-scoped data.
    """
    from app.core.database import get_db
    from app.main import app

    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
    app.dependency_overrides.clear()


async def login(client: AsyncClient, email: str, password: str = DEFAULT_PASSWORD) -> str:
    """Authenticate and return the access token."""
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


__all__ = [
    "DEFAULT_PASSWORD",
    "UserRole",
    "auth_header",
    "login",
]
