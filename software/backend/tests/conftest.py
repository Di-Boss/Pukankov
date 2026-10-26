import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.main import app
from app.db import Base, make_engine, get_db
from app.seed import seed
from app.models import User
from app.core.security import hash_password, limiter


@pytest.fixture
def setup(tmp_path):
    engine = make_engine(f'sqlite:///{tmp_path / "test.db"}')
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory() as db:
        seed(db)
        db.add(
            User(
                email="admin@example.com",
                name="Test Admin",
                role="admin",
                password_hash=hash_password("TestPassword123!"),
            )
        )
        db.commit()

    def override():
        with factory() as db:
            try:
                yield db
                db.commit()
            except Exception:
                db.rollback()
                raise

    app.dependency_overrides[get_db] = override
    limiter.attempts.clear()
    with TestClient(app, headers={"X-Requested-With": "Pukankov"}) as client:
        yield client, factory
    app.dependency_overrides.clear()
    engine.dispose()


def register(client, email="viewer@example.com"):
    return client.post(
        "/api/v1/auth/register",
        json={
            "name": "Кино Зрител",
            "email": email,
            "password": "TestPassword123!",
            "terms": True,
        },
    )


@pytest.fixture
def viewer(setup):
    client, factory = setup
    assert register(client).status_code == 201
    return client, factory


@pytest.fixture
def admin(setup):
    client, factory = setup
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "TestPassword123!"},
        ).status_code
        == 200
    )
    return client, factory
