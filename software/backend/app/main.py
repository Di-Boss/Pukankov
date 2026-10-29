import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError
from .core.config import settings
from .api import public, auth, booking, admin, devices

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app):
    if settings.environment == "production" and settings.database_url.startswith(
        "sqlite"
    ):
        raise RuntimeError("Production requires PostgreSQL and migrations.")
    yield


app = FastAPI(
    title="Пуканков API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.environment != "production" else None,
    openapi_url="/api/openapi.json" if settings.environment != "production" else None,
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    device_path = request.url.path.startswith(("/api/v1/devices/", "/api/validator/"))
    if (
        request.method not in ("GET", "HEAD", "OPTIONS")
        and request.url.path.startswith("/api")
        and not device_path
    ):
        origin = request.headers.get("origin")
        allowed = (
            {
                settings.public_origin,
                "http://localhost:5173",
                "http://127.0.0.1:5173",
                "http://localhost:4173",
                "http://127.0.0.1:4173",
                "http://localhost:8000",
                "http://127.0.0.1:8000",
            }
            if settings.environment != "production"
            else {settings.public_origin}
        )
        # Non-simple custom header plus same-origin policy blocks cross-site form CSRF.
        if request.headers.get("x-requested-with") != "Pukankov" or (
            origin and origin not in allowed
        ):
            return JSONResponse(
                {"detail": "Невалиден произход на заявката."}, status_code=403
            )
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' https: data:; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; script-src 'self'; frame-src https://www.youtube-nocookie.com; connect-src 'self' ws:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
    )
    if request.url.path.startswith("/api"):
        response.headers["Cache-Control"] = "no-store"
    if settings.environment == "production":
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
    return response


@app.exception_handler(IntegrityError)
async def integrity_error(request, exc):
    logging.getLogger("pukankov").warning(
        "Database constraint conflict on %s", request.url.path
    )
    return JSONResponse(
        {
            "detail": "Записът вече съществува или данните са в конфликт. Обновете страницата."
        },
        status_code=409,
    )


app.include_router(public.router)
app.include_router(auth.router)
app.include_router(booking.router)
app.include_router(admin.router)
app.include_router(devices.router)
app.include_router(devices.validator_router)

dist = Path(__file__).resolve().parents[2] / "dist"
if dist.exists():
    app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str):
        if path.startswith("api/"):
            return JSONResponse({"detail": "Not found"}, status_code=404)
        target = (dist / path).resolve()
        if target.is_relative_to(dist.resolve()) and target.is_file():
            return FileResponse(target)
        return FileResponse(dist / "index.html")
