# Turf Booking System

A full-stack turf (sports ground) booking platform. The backend is built with
**Python**, **FastAPI**, **PostgreSQL**, **SQLAlchemy 2.0**, **Alembic**,
**Pydantic v2**, and **JWT** authentication. A React frontend will follow.

---

## Architecture

```
turf-booking-system/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI factory, CORS, exception handlers, /health
│   │   ├── core/              # config, database, security, deps, exceptions, logging
│   │   ├── models/            # SQLAlchemy ORM + enums
│   │   ├── schemas/           # Pydantic request/response models
│   │   ├── services/          # all business logic
│   │   └── api/v1/endpoints/  # thin HTTP routers
│   ├── alembic/               # migrations
│   ├── scripts/seed.py        # development seed data
│   └── tests/                 # unit + integration
├── docker-compose.yml         # PostgreSQL 16
└── .env.example
```

**Layering rule:** `api → schemas → services → models → database`.
Routers only parse, validate, call a service, and serialise. No booking rule
lives in a router, and no service knows about HTTP.

### Domain model

| Entity | Purpose |
|---|---|
| `Role` | `admin` / `owner` / `customer`, seeded by migration |
| `User` | Account, Argon2id password hash, role, active/verified flags |
| `RefreshToken` | Server-side session record backing the refresh cookie |
| `Turf` | A bookable pitch, owned by a user, with an hourly rate |
| `TurfSchedule` | Recurring weekly availability window |
| `Booking` | A reserved time range, its status, and its payment state |

### Double-booking is prevented by the database

An application-level overlap check alone is not sufficient: two concurrent
requests can both pass it. The real guarantee is a PostgreSQL exclusion
constraint created in the initial migration:

```sql
ALTER TABLE bookings
ADD CONSTRAINT no_overlapping_bookings
EXCLUDE USING gist (
    turf_id WITH =,
    tstzrange(start_time, end_time) WITH &&
) WHERE (status IN ('pending', 'confirmed'))
```

The service still performs a pre-check, but only to return a friendly `409` in
the common case; when a race is lost the constraint fires and the service
translates the `IntegrityError` into the same `409`. A matching constraint on
`turf_schedules` prevents a turf from having two overlapping windows on one day.

Intervals are treated as **half-open** (`[start, end)`), so a booking ending at
11:00 and one starting at 11:00 do not conflict.

### Authentication

- **Access token** — short-lived JWT (30 min), returned in the response body for
  the SPA to hold in memory. Stateless.
- **Refresh token** — 384 bits of CSPRNG output in an `httpOnly`, `SameSite`
  cookie scoped to `/api/v1/auth`. Only its SHA-256 hash is stored.
- **Rotation** — every refresh revokes the presented token and issues a
  successor linked via `replaced_by_id`.
- **Reuse detection** — replaying an already-revoked token is treated as theft:
  every token in that family is revoked and the user must sign in again.
- **Revocation on security events** — password change, deactivation, and
  admin-initiated demotion all revoke the user's active sessions.

Passwords use Argon2id via `pwdlib`.

### Payments

Cash on site only in v1. `Booking.payment_status` moves between `unpaid`,
`paid_on_site`, and `refunded`; an admin marks payment received. Online capture
can be added later as a payment adapter without changing the booking flow.

---

## Getting started

### Prerequisites

- [uv](https://docs.astral.sh/uv/) — `irm https://astral.sh/uv/install.ps1 | iex`
- Docker Desktop (for PostgreSQL)

### 1. Start the database

```powershell
docker compose up -d
```

The compose service publishes on **5433** by default because a local PostgreSQL
install commonly occupies 5432. Override with `POSTGRES_PORT` if needed.

### 2. Configure the backend

```powershell
cd backend
Copy-Item ..\.env.example .env
```

Generate a real signing key:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Paste it into `JWT_SECRET_KEY` in `.env`.

### 3. Install dependencies

```powershell
uv venv --python 3.13
uv pip install -e ".[dev]"
```

### 4. Migrate and seed

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m scripts.seed
```

The seed is idempotent and creates:

| Email | Password | Role |
|---|---|---|
| `admin@example.com` | `Admin@12345` | admin |
| `owner@example.com` | `Owner@12345` | owner |
| `customer@example.com` | `Customer@12345` | customer |

### 5. Run the API

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

- Swagger UI: <http://127.0.0.1:8000/docs>
- Health: <http://127.0.0.1:8000/health>

---

## Development

```powershell
# Run everything (unit + integration)
.\.venv\Scripts\python.exe -m pytest

# Unit tests only - no database needed
.\.venv\Scripts\python.exe -m pytest tests/unit

# Lint and format
.\.venv\Scripts\python.exe -m ruff check app tests scripts
.\.venv\Scripts\python.exe -m ruff format app tests scripts

# Strict type checking
.\.venv\Scripts\python.exe -m mypy app

# New migration after changing a model
.\.venv\Scripts\python.exe -m alembic revision --autogenerate -m "describe change"
```

Integration tests run against `turf_booking_test` and recreate the schema for
each test. Create it once:

```powershell
docker exec turf_db psql -U turf -d postgres -c "CREATE DATABASE turf_booking_test OWNER turf"
```

Override the target with `TEST_DATABASE_URL`.

> If `ruff` is not on your `PATH`, add the venv's scripts directory before running
> Alembic — the `post_write_hooks` step invokes `ruff` as a subprocess:
> `$env:Path = "$PWD\.venv\Scripts;$env:Path"`

---

## API overview

All routes are under `/api/v1`.

### Auth
| Method | Path | Notes |
|---|---|---|
| `POST` | `/auth/register` | Customer self-registration; sets refresh cookie |
| `POST` | `/auth/login` | Returns access token, sets refresh cookie |
| `POST` | `/auth/refresh` | Rotates the refresh cookie, returns a new access token |
| `POST` | `/auth/logout` | Revokes the current session |
| `POST` | `/auth/logout-all` | Revokes every session for the caller |
| `GET` | `/auth/me` | Current profile |

### Turfs
| Method | Path | Notes |
|---|---|---|
| `GET` | `/turfs` | Active turfs, filterable by city |
| `POST` | `/turfs` | Owner or admin |
| `GET` | `/turfs/{id}` | |
| `PATCH` | `/turfs/{id}` | Owner of the turf, or admin |
| `DELETE` | `/turfs/{id}` | Soft delete |
| `GET` | `/turfs/{id}/availability?date=YYYY-MM-DD` | Generated slots with availability |
| `GET`/`POST` | `/turfs/{id}/schedules` | Weekly availability windows |
| `PATCH`/`DELETE` | `/turfs/{id}/schedules/{sid}` | |

### Bookings
| Method | Path | Notes |
|---|---|---|
| `POST` | `/bookings` | Returns `409 booking_conflict` on overlap |
| `GET` | `/bookings` | Customers see their own; owners also see their turfs' |
| `GET` | `/bookings/{id}` | |
| `POST` | `/bookings/{id}/cancel` | |
| `PATCH` | `/bookings/{id}` | Admin: status transitions, mark paid |

### Users (admin)
| Method | Path | Notes |
|---|---|---|
| `GET` | `/users` | List and search |
| `POST` | `/users` | Provision an owner or admin |
| `PATCH` | `/users/{id}` | Update role/flags; deactivation revokes sessions |
| `DELETE` | `/users/{id}` | Deactivate |
| `PATCH` | `/users/me/password` | Revokes all sessions on success |

### Errors

```json
{
  "error": {
    "code": "booking_conflict",
    "message": "That time slot has just been booked. Please choose another slot.",
    "details": null
  }
}
```

---

## Docker

`backend/Dockerfile` is a two-stage uv build on `python:3.13-slim`, running as a
non-root user with a health check.

```powershell
cd backend
docker build -t turf-api .
docker run -p 8000:8000 --env-file .env turf-api
```

---

## Not yet built

- React frontend
- Online payments (the booking flow is already adapter-ready)
- Email verification, password reset, and refresh of invites
- Turf photos, reviews, and ratings
- Availability exceptions (holidays, one-off closures)
