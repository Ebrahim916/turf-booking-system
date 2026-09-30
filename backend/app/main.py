"""FastAPI application factory and global exception handlers."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import engine
from app.core.exceptions import AppError
from app.core.logging import configure_logging, logger

DESCRIPTION = """
REST API for booking turf (sports ground) time slots.

**Authentication** uses a short-lived JWT access token returned in the response
body, plus a rotating refresh token in an httpOnly cookie. Send the access token
as `Authorization: Bearer <token>`.

**Roles** are `admin`, `owner`, and `customer`.
"""


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    logger.info("starting", environment=settings.environment)
    yield
    await engine.dispose()
    logger.info("shutdown complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description=DESCRIPTION,
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Credentials must be allowed for the refresh cookie, and Starlette rejects a
    # wildcard origin when they are - hence the explicit settings.cors_origins list.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(AppError)
    async def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                }
            },
            headers=({"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # `ctx` can hold the original exception object (e.g. the ValueError raised
        # by a custom validator), which is not JSON-serialisable. The `msg` already
        # carries the human-readable reason, so drop `ctx` rather than stringify it.
        details = [
            {key: value for key, value in error.items() if key != "ctx"} for error in exc.errors()
        ]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={
                "error": {
                    "code": "request_validation_error",
                    "message": "The request payload or query is invalid.",
                    "details": details,
                }
            },
        )

    @app.get("/health", tags=["system"], summary="Liveness and database probe")
    async def health() -> dict[str, object]:
        db_ok = True
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        except Exception:  # pragma: no cover - depends on infrastructure
            db_ok = False
        return {
            "status": "ok" if db_ok else "degraded",
            "database": "ok" if db_ok else "unavailable",
            "environment": settings.environment,
            "version": app.version,
        }

    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
