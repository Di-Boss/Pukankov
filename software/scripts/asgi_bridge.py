"""Isolated, socket-free ASGI transport for browser tests in restricted Windows CI.

Only the test harness uses polling; the application keeps its normal event loop.
All HTTP requests still traverse the complete FastAPI app and database services.
"""

import asyncio
import base64
import json
import logging
import os
from pathlib import Path
import selectors
import sys
import time


if sys.platform == "win32":

    class PollingSelector(selectors.SelectSelector):
        def select(self, timeout=None):
            timeout = min(timeout, 0.01) if timeout is not None else 0.01
            if not self.get_map():
                time.sleep(max(timeout, 0))
                return []
            return super().select(timeout)

    class TestLoop(asyncio.SelectorEventLoop):
        def __init__(self):
            super().__init__(PollingSelector())

        def _make_self_pipe(self):
            self._ssock = None
            self._csock = None

        def _close_self_pipe(self):
            pass

        def _write_to_self(self):
            pass

    class Policy(asyncio.WindowsSelectorEventLoopPolicy):
        _loop_factory = TestLoop

    asyncio.set_event_loop_policy(Policy())

root = Path(__file__).resolve().parents[1] / "backend"
os.chdir(root)
sys.path.insert(0, str(root))
if not os.environ.get("PUKANKOV_E2E_PASSWORD") or not os.environ.get(
    "DATABASE_URL", ""
).startswith("sqlite:"):
    raise SystemExit(
        "An isolated SQLite test database and generated E2E password are required."
    )
from app.db import Base, engine, SessionLocal
from app.seed import seed
from app.models import User
from app.core.security import hash_password
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy import select

Base.metadata.create_all(engine)
with SessionLocal() as db:
    seed(db)
    if not db.scalar(select(User).where(User.email == "e2e-admin@example.com")):
        db.add(
            User(
                name="E2E Admin",
                email="e2e-admin@example.com",
                role="admin",
                password_hash=hash_password(os.environ["PUKANKOV_E2E_PASSWORD"]),
            )
        )
    db.commit()
logging.getLogger("httpx").setLevel(logging.ERROR)
with TestClient(app, raise_server_exceptions=False) as client:
    print(json.dumps({"ready": True}), flush=True)
    for raw in sys.stdin:
        request = json.loads(raw)
        # Browser contexts own their cookie jars; never share cookies across requests here.
        client.cookies.clear()
        response = client.request(
            request["method"],
            request["url"],
            headers=request.get("headers", {}),
            content=request.get("body") or None,
            follow_redirects=False,
        )
        headers = dict(response.headers)
        for key in ("content-length", "content-encoding", "transfer-encoding"):
            headers.pop(key, None)
        print(
            json.dumps(
                {
                    "id": request["id"],
                    "status": response.status_code,
                    "headers": headers,
                    "body": base64.b64encode(response.content).decode("ascii"),
                }
            ),
            flush=True,
        )
