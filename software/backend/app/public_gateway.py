"""Internet-facing API: device authentication, catalog, seats and terminal payment only.

Run separately from the website against the exact same DATABASE_URL.
There are no account, admin, database-download or card-registration routes here.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from .db import get_db
from .core.config import settings
from .api import devices


@asynccontextmanager
async def lifespan(app):
    if settings.environment == "production" and settings.database_url.startswith(
        "sqlite"
    ):
        raise RuntimeError("Production requires PostgreSQL and migrations.")
    yield


app = FastAPI(
    title="Pukankov ESP32 ticket API",
    version="1.1.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url=None,
)


@app.middleware("http")
async def headers(request: Request, call_next):
    # Avoid reflecting RFID UIDs into request logs. Uvicorn access logs contain paths only.
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@app.exception_handler(IntegrityError)
async def conflict(request, exc):
    return JSONResponse(
        {
            "detail": {
                "reason": "conflict",
                "message": "Мястото или поръчката вече са заети. Обнови наличността.",
            }
        },
        status_code=409,
    )


@app.get("/", include_in_schema=False)
def api_info():
    return {
        "service": "Pukankov ESP32 ticket API",
        "docs": "/api/docs",
        "health": "/api/v1/health",
    }


@app.get("/api/v1/health", tags=["Status"])
def health(db: Session = Depends(get_db)):
    db.execute(select(1))
    return {
        "status": "ok",
        "service": "pukankov-device-api",
        "payment_mode": "terminal_signal",
        "balance_enabled": False,
        "timezone": "Europe/Sofia",
    }


app.include_router(devices.router)
app.include_router(devices.validator_router)
