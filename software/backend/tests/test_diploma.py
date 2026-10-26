import os
import re
import secrets
import subprocess
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from sqlalchemy import select, func, create_engine, MetaData
from app.db import utcnow
from app.models import Device, User, Ticket, Payment, Showtime, Movie, Booking
from app.core.security import digest, hash_password
from app.services.tickets import validate_ticket
from app.seed import seed
from app.original_catalog import movie_records
from test_platform import choose, held, paid


def device(factory, role, auditorium_id=None):
    key = secrets.token_urlsafe(32)
    with factory() as db:
        user = User(
            name="Test terminal",
            email=secrets.token_hex(8) + "@example.com",
            active=False,
            password_hash=hash_password(secrets.token_urlsafe(20)),
        )
        db.add(user)
        db.flush()
        obj = Device(
            id=secrets.token_hex(12),
            name="Test terminal",
            role=role,
            key_hash=digest(key),
            user_id=user.id,
            auditorium_id=auditorium_id,
        )
        db.add(obj)
        db.commit()
        return obj.id, {"Authorization": "Bearer " + key}


def test_unchecked_transaction_issues_no_ticket(viewer):
    client, factory = viewer
    show, seats, h = held(client)
    response = client.post(
        "/api/v1/payments/checkout", json={"hold_id": h["id"], "terms": True}
    )
    assert response.status_code == 200 and response.json()["status"] == "cancelled"
    assert response.json()["items"] == []
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(Ticket)) == 0
        assert db.scalar(select(Payment)).status == "failed"
    assert (
        client.post(
            "/api/v1/bookings/holds",
            json={"showtime_id": show["id"], "seat_ids": seats},
        ).status_code
        == 201
    )


def test_codes_are_six_ascii_digits_unique_and_no_qr_data(viewer):
    client, _ = viewer
    *_, booking = paid(client, 6)
    codes = [i["ticket_code"] for i in booking["items"]]
    assert len(set(codes)) == 6 and all(
        re.fullmatch(r"[0-9]{6}", code) for code in codes
    )
    assert all("qr_token" not in i and "scan_hash" not in i for i in booking["items"])


def test_code_collision_retries_without_partial_order(viewer, monkeypatch):
    client, _ = viewer
    *_, first = paid(client)
    value = int(first["items"][0]["ticket_code"]) - 100000
    sequence = iter([value, (value + 1) % 900000])
    monkeypatch.setattr(
        "app.services.tickets.secrets.randbelow", lambda _: next(sequence)
    )
    *_, second = paid(client)
    assert second["status"] == "confirmed"
    assert first["items"][0]["ticket_code"] != second["items"][0]["ticket_code"]


def test_wrong_screening_does_not_consume_code(viewer):
    client, _ = viewer
    *_, booking = paid(client)
    client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "TestPassword123!"},
    )
    code = booking["items"][0]["ticket_code"]
    show_id = booking["showtime"]["id"]
    wrong = client.post(
        "/api/v1/staff/tickets/validate",
        json={"ticket_code": code, "showtime_id": show_id + 9999},
    ).json()
    assert wrong["valid"] is False and wrong["reason"] == "wrong_showtime"
    good = client.post(
        "/api/v1/staff/tickets/validate",
        json={"ticket_code": code, "showtime_id": show_id},
    ).json()
    assert good["valid"] is True
    assert (
        client.post(
            "/api/v1/staff/tickets/validate",
            json={"ticket_code": "ABC123", "showtime_id": show_id},
        ).status_code
        == 422
    )


def test_two_validators_cannot_consume_the_same_code(viewer):
    client, factory = viewer
    *_, booking = paid(client)
    user_id = client.get("/api/v1/me").json()["id"]
    barrier = Barrier(2)

    def run(_):
        barrier.wait(timeout=10)
        with factory() as db:
            result = validate_ticket(
                db,
                booking["items"][0]["ticket_code"],
                booking["showtime"]["id"],
                user_id,
            )
            db.commit()
            return result["valid"]

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(run, range(2))) == [False, True]


def test_expired_and_cancelled_screenings_reject_ticket(viewer):
    client, factory = viewer
    *_, booking = paid(client)
    user_id = client.get("/api/v1/me").json()["id"]
    with factory() as db:
        show = db.get(Showtime, booking["showtime"]["id"])
        show.cancelled = True
        db.commit()
        result = validate_ticket(
            db, booking["items"][0]["ticket_code"], show.id, user_id
        )
        assert result["reason"] == "cancelled"
        show.cancelled = False
        show.ends_at = utcnow() - timedelta(minutes=1)
        db.commit()
        result = validate_ticket(
            db, booking["items"][0]["ticket_code"], show.id, user_id
        )
        assert result["reason"] == "expired"


def test_website_kiosk_and_keypad_share_inventory_and_tickets(viewer):
    client, factory = viewer
    _, kiosk_headers = device(factory, "kiosk")
    _, validator_headers = device(factory, "validator")
    show, seats = choose(client)
    hold = client.post(
        "/api/v1/devices/bookings/holds",
        headers=kiosk_headers,
        json={"showtime_id": show["id"], "seat_ids": seats},
    )
    assert hold.status_code == 201
    assert (
        client.post(
            "/api/v1/bookings/holds",
            json={"showtime_id": show["id"], "seat_ids": seats},
        ).status_code
        == 409
    )
    data = {"hold_id": hold.json()["id"], "terms": True, "transaction_success": True}
    purchased = client.post(
        "/api/v1/devices/payments/checkout", headers=kiosk_headers, json=data
    ).json()
    assert purchased["success"] is True and re.fullmatch(
        "[0-9]{6}", purchased["ticket_code"]
    )
    again = client.post(
        "/api/v1/devices/payments/checkout", headers=kiosk_headers, json=data
    ).json()
    assert (
        again["booking_id"] == purchased["booking_id"]
        and again["ticket_code"] == purchased["ticket_code"]
    )
    check = {"ticket_code": purchased["ticket_code"], "showtime_id": show["id"]}
    assert client.post(
        "/api/validator/validate", headers=validator_headers, json=check
    ).json()["valid"]
    assert (
        client.post(
            "/api/v1/devices/tickets/validate", headers=validator_headers, json=check
        ).json()["reason"]
        == "already_used"
    )


def test_device_auth_roles_scope_and_revocation(viewer):
    client, factory = viewer
    key_id, headers = device(factory, "validator")
    show, seats = choose(client)
    assert client.get("/api/v1/devices/showtimes").status_code == 401
    assert (
        client.post(
            "/api/v1/devices/bookings/holds",
            headers=headers,
            json={"showtime_id": show["id"], "seat_ids": seats},
        ).status_code
        == 403
    )
    _, scoped = device(factory, "kiosk", auditorium_id=show["auditorium_id"])
    other = next(
        s
        for s in client.get("/api/v1/showtimes").json()
        if s["auditorium_id"] != show["auditorium_id"]
    )
    assert (
        client.get(
            f'/api/v1/devices/showtimes/{other["id"]}/seats', headers=scoped
        ).status_code
        == 403
    )
    with factory() as db:
        db.get(Device, key_id).active = False
        db.commit()
    assert client.get("/api/v1/devices/showtimes", headers=headers).status_code == 401


def test_numeric_code_attempts_are_rate_limited(viewer):
    client, factory = viewer
    _, headers = device(factory, "validator")
    show, _ = choose(client)
    for _ in range(30):
        assert (
            client.post(
                "/api/validator/validate",
                headers=headers,
                json={"ticket_code": "000000", "showtime_id": show["id"]},
            ).status_code
            == 200
        )
    assert (
        client.post(
            "/api/validator/validate",
            headers=headers,
            json={"ticket_code": "000000", "showtime_id": show["id"]},
        ).status_code
        == 429
    )


def test_original_catalog_retains_existing_accounts_and_purchases(viewer):
    client, factory = viewer
    *_, booking = paid(client)
    with factory() as db:
        movie = db.get(Movie, booking["showtime"]["movie_id"])
        movie.slug = "dune-part-two"
        movie.title = "Legacy film"
        db.commit()
        seed(db)
        assert db.get(Movie, movie.id).in_catalog is False
        assert db.get(Booking, booking["id"]).status == "confirmed"
    assert client.get("/api/v1/movies").json()["total"] == 15
    assert (
        client.get("/api/v1/bookings/" + booking["id"]).json()["items"][0][
            "ticket_code"
        ]
        == booking["items"][0]["ticket_code"]
    )
    assert all(
        s["movie"]["slug"] != "dune-part-two"
        for s in client.get("/api/v1/showtimes").json()
    )


def test_upgrade_converts_old_ticket_without_losing_history(tmp_path):
    url = "sqlite:///" + str(tmp_path / "legacy.db").replace("\\", "/")
    env = {**os.environ, "DATABASE_URL": url}
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "0001"],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        check=True,
        capture_output=True,
    )
    engine = create_engine(url)
    meta = MetaData()
    meta.reflect(engine)
    now = utcnow()
    with engine.begin() as conn:

        def insert(table, **values):
            conn.execute(meta.tables[table].insert().values(**values))

        insert(
            "users",
            id=1,
            email="old@example.com",
            name="Old owner",
            password_hash="unused",
            role="user",
            active=True,
            deletion_requested=False,
            created_at=now,
        )
        m = next(movie_records())
        m.pop("in_catalog")
        m.update(id=1, created_at=now, updated_at=now)
        insert("movies", **m)
        insert(
            "cinemas",
            id=1,
            name="Cinema",
            slug="cinema",
            city="Sofia",
            address="Test address",
            description="Test",
            image="",
            is_demo=True,
        )
        insert("auditoriums", id=1, cinema_id=1, name="Room", formats=["2D"])
        insert(
            "seats",
            id=1,
            auditorium_id=1,
            row="A",
            number=1,
            category="standard",
            surcharge=0,
            accessible=False,
            active=True,
        )
        insert(
            "showtimes",
            id=1,
            movie_id=1,
            auditorium_id=1,
            starts_at=now + timedelta(days=1),
            ends_at=now + timedelta(days=1, hours=2),
            price=12,
            format="2D",
            cancelled=False,
            is_demo=True,
        )
        insert(
            "holds",
            id="legacy-hold",
            user_id=1,
            showtime_id=1,
            expires_at=now + timedelta(minutes=5),
            status="completed",
        )
        insert(
            "bookings",
            id="OLD-ORDER",
            user_id=1,
            hold_id="legacy-hold",
            showtime_id=1,
            total=12,
            discount=0,
            currency="EUR",
            status="confirmed",
            is_demo=True,
            created_at=now,
        )
        insert(
            "showtime_seat_claims",
            id=1,
            showtime_id=1,
            seat_id=1,
            hold_id="legacy-hold",
            booking_id="OLD-ORDER",
            price=12,
        )
        insert(
            "tickets",
            id="old-ticket",
            booking_id="OLD-ORDER",
            claim_id=1,
            scan_hash="a" * 64,
            qr_token="legacy-qr-token",
            used_at=now,
        )
    engine.dispose()
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        check=True,
        capture_output=True,
    )
    engine = create_engine(url)
    meta = MetaData()
    meta.reflect(engine)
    with engine.connect() as conn:
        row = conn.execute(meta.tables["tickets"].select()).mappings().one()
        assert row["booking_id"] == "OLD-ORDER" and row["used_at"] is not None
        assert re.fullmatch("[0-9]{6}", row["ticket_code"])
        assert "qr_token" not in row and "scan_hash" not in row
    engine.dispose()
