"""Isolated local E2E fixture. Never run against a production database."""

import os
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
backend = root / "backend"
os.chdir(backend)
sys.path.insert(0, str(backend))
if not os.environ.get("PUKANKOV_E2E_PASSWORD") or not os.environ.get(
    "DATABASE_URL", ""
).startswith("sqlite:"):
    raise SystemExit(
        "This test server requires an isolated SQLite DATABASE_URL and a generated E2E password."
    )
from app.db import Base, engine, SessionLocal
from app.seed import seed
from app.models import User
from app.core.security import hash_password

Base.metadata.create_all(engine)
with SessionLocal() as db:
    seed(db)
    db.add(
        User(
            name="E2E Admin",
            email="e2e-admin@example.com",
            role="admin",
            password_hash=hash_password(os.environ["PUKANKOV_E2E_PASSWORD"]),
        )
    )
    db.commit()
import uvicorn

uvicorn.run("app.main:app", host="127.0.0.1", port=8001, log_level="warning")
