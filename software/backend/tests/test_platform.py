from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta, timezone
from threading import Barrier
from fastapi import HTTPException
from sqlalchemy import select, func
from app.db import utcnow
from app.models import User, Hold, SeatClaim, Ticket, Showtime, Booking
from app.schemas import HoldInput
from app.services.reservations import create_hold
from app.core.security import hash_password
from conftest import register


def choose(client, count=1):
    show = client.get("/api/v1/showtimes").json()[0]
    seats = client.get(f'/api/v1/showtimes/{show["id"]}/seats').json()["seats"]
    selected = [s["id"] for s in seats if s["status"] == "available"][:count]
    return show, selected


def held(client, count=1):
    show, seats = choose(client, count)
    response = client.post(
        "/api/v1/bookings/holds", json={"showtime_id": show["id"], "seat_ids": seats}
    )
    assert response.status_code == 201, response.text
    return show, seats, response.json()


def paid(client, count=1, **extra):
    show, seats, h = held(client, count)
    response = client.post(
        "/api/v1/payments/checkout",
        json={"hold_id": h["id"], "terms": True, "transaction_success": True, **extra},
    )
    assert response.status_code == 200, response.text
    return show, seats, h, response.json()


def test_seed_and_api_catalog(setup):
    client, _ = setup
    result = client.get("/api/v1/movies?page_size=50").json()
    assert result["total"] == 15
    assert all(m["is_demo"] for m in result["items"])
    assert client.get("/api/v1/movies/featured").json()[0]["slug"] == "last-orbit"
    assert len(client.get("/api/v1/movies/top").json()) == 10


def test_timestamps_roundtrip_as_aware_utc(setup):
    client, factory = setup
    with factory() as db:
        show = db.scalar(select(Showtime).order_by(Showtime.id))
        assert show.starts_at.tzinfo is not None
        assert show.starts_at.utcoffset() == timedelta(0)
    assert client.get("/api/v1/showtimes").json()[0]["starts_at"].endswith("+00:00")


def test_bulgarian_search_and_filters(setup):
    client, _ = setup
    r = client.get("/api/v1/movies", params={"q": "ПОСЛЕДНАТА ОРБИТА"}).json()
    assert r["total"] == 1 and r["items"][0]["slug"] == "last-orbit"
    r = client.get(
        "/api/v1/movies",
        params={
            "genre": "Анимация",
            "language": "Български",
            "max_duration": 110,
            "min_rating": 7,
        },
    ).json()
    assert r["total"] > 0
    assert all("Анимация" in m["genres"] and m["duration"] <= 110 for m in r["items"])
    assert client.get("/api/v1/movies?q=nonexistent-movie").json()["total"] == 0


def test_registration_login_logout_and_cookie(setup):
    client, _ = setup
    assert register(client).status_code == 201
    assert (
        "HttpOnly"
        in client.post(
            "/api/v1/auth/login",
            json={"email": "viewer@example.com", "password": "TestPassword123!"},
        ).headers["set-cookie"]
    )
    assert client.get("/api/v1/me").json()["role"] == "user"
    assert register(client).status_code == 409
    assert client.post("/api/v1/auth/logout").status_code == 200
    assert client.get("/api/v1/me").status_code == 401
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"email": "viewer@example.com", "password": "wrong"},
        ).status_code
        == 401
    )


def test_registration_validation_and_role_escalation(setup):
    client, _ = setup
    assert (
        client.post(
            "/api/v1/auth/register",
            json={"name": "A", "email": "bad", "password": "short", "terms": False},
        ).status_code
        == 422
    )
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Viewer",
            "email": "user@example.com",
            "password": "TestPassword123!",
            "terms": True,
            "role": "admin",
        },
    )
    assert response.status_code == 201
    assert response.json()["role"] == "user"


def test_access_control_and_favorites(viewer):
    client, _ = viewer
    assert client.get("/api/v1/admin/dashboard").status_code == 403
    assert client.post("/api/v1/me/favorites/1").status_code == 200
    assert client.get("/api/v1/me/favorites").json()[0]["id"] == 1
    assert client.delete("/api/v1/me/favorites/1").status_code == 200
    assert client.get("/api/v1/me/favorites").json() == []


def test_local_login_origins(viewer):
    client, _ = viewer
    for origin in (
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ):
        response = client.post(
            "/api/v1/auth/login",
            headers={"Origin": origin},
            json={"email": "viewer@example.com", "password": "TestPassword123!"},
        )
        assert response.status_code == 200, (origin, response.text)
        assert client.get("/api/v1/me").status_code == 200
    assert client.post(
        "/api/v1/auth/logout",
        headers={"Origin": "http://localhost:8000", "X-Requested-With": ""},
    ).status_code == 403


def test_production_login_origin_remains_restricted(setup, monkeypatch):
    from app.core.config import settings

    client, _ = setup
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "public_origin", "https://cinema.example")
    for origin in ("http://localhost:8000", "http://127.0.0.1:8000", "https://evil.example"):
        assert client.post(
            "/api/v1/auth/login", headers={"Origin": origin}, json={}
        ).status_code == 403
    assert client.post(
        "/api/v1/auth/login", headers={"Origin": "https://cinema.example"}, json={}
    ).status_code == 422


def test_csrf_and_origin_rejected(viewer):
    client, _ = viewer
    assert (
        client.post(
            "/api/v1/auth/logout",
            headers={"X-Requested-With": "", "Origin": "https://evil.example"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/auth/logout", headers={"Origin": "https://evil.example"}
        ).status_code
        == 403
    )
    assert client.get("/api/v1/me").status_code == 200


def test_missing_resources(setup):
    client, _ = setup
    assert client.get("/api/v1/movies/slug/no-such-film").status_code == 404
    assert client.get("/api/v1/showtimes/999999/seats").status_code == 404
    assert client.get("/api/v1/showtimes?date=bad-date").status_code == 422


def test_unauthenticated_hold_rejected(setup):
    client, _ = setup
    show, seats = choose(client)
    assert (
        client.post(
            "/api/v1/bookings/holds",
            json={"showtime_id": show["id"], "seat_ids": seats},
        ).status_code
        == 401
    )


def test_hold_conflict_and_release(viewer):
    client, _ = viewer
    show, seats, h = held(client)
    assert (
        client.post(
            "/api/v1/bookings/holds",
            json={"showtime_id": show["id"], "seat_ids": seats},
        ).status_code
        == 409
    )
    status = client.get(f'/api/v1/showtimes/{show["id"]}/seats').json()
    assert next(s for s in status["seats"] if s["id"] == seats[0])["status"] == "held"
    assert client.delete("/api/v1/bookings/holds/" + h["id"]).status_code == 200
    assert (
        client.post(
            "/api/v1/bookings/holds",
            json={"showtime_id": show["id"], "seat_ids": seats},
        ).status_code
        == 201
    )


def test_hold_expiration_and_payment_rejected(viewer):
    client, factory = viewer
    show, seats, h = held(client)
    with factory() as db:
        db.get(Hold, h["id"]).expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
    assert (
        client.post(
            "/api/v1/payments/checkout", json={"hold_id": h["id"], "terms": True}
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/api/v1/bookings/holds",
            json={"showtime_id": show["id"], "seat_ids": seats},
        ).status_code
        == 201
    )


def test_duplicate_seats_and_wrong_room_rejected(viewer):
    client, _ = viewer
    show, seats = choose(client)
    assert (
        client.post(
            "/api/v1/bookings/holds",
            json={"showtime_id": show["id"], "seat_ids": [seats[0], seats[0]]},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/bookings/holds",
            json={"showtime_id": show["id"], "seat_ids": [999999]},
        ).status_code
        == 422
    )


def test_checkout_is_idempotent_and_tickets_opaque(viewer):
    client, factory = viewer
    show, seats, h, b = paid(client, 2)
    again = client.post(
        "/api/v1/payments/checkout", json={"hold_id": h["id"], "terms": True}
    ).json()
    assert b["id"] == again["id"]
    assert b["is_demo"] and b["status"] == "confirmed" and len(b["items"]) == 2
    assert (
        b["items"][0]["ticket_code"].isdigit()
        and len(b["items"][0]["ticket_code"]) == 6
    )
    assert "qr_token" not in b["items"][0]
    assert client.get("/api/v1/me/tickets").json()[0]["id"] == b["id"]
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(Ticket)) == 2
    assert (
        client.post(
            "/api/v1/bookings/holds",
            json={"showtime_id": show["id"], "seat_ids": seats},
        ).status_code
        == 409
    )


def test_order_and_hold_ownership(viewer):
    client, _ = viewer
    _, _, h, b = paid(client)
    client.post("/api/v1/auth/logout")
    register(client, "other@example.com")
    assert client.get("/api/v1/bookings/" + b["id"]).status_code == 404
    assert client.get("/api/v1/bookings/holds/" + h["id"]).status_code == 404
    assert client.get("/api/v1/me/tickets").json() == []


def test_invalid_promotion(viewer):
    client, _ = viewer
    _, _, h = held(client, 2)
    assert (
        client.post(
            "/api/v1/promotions/validate", json={"hold_id": h["id"], "code": "NOPE"}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/payments/checkout",
            json={"hold_id": h["id"], "terms": True, "promo_code": "NOPE"},
        ).status_code
        == 422
    )


def test_promotion_calculated_by_server(viewer):
    client, _ = viewer
    _, _, h = held(client, 2)
    p = client.post(
        "/api/v1/promotions/validate", json={"hold_id": h["id"], "code": "KINO20"}
    ).json()
    b = client.post(
        "/api/v1/payments/checkout",
        json={
            "hold_id": h["id"],
            "terms": True,
            "transaction_success": True,
            "promo_code": "KINO20",
            "total": 0.01,
        },
    ).json()
    assert (
        b["discount"] == p["discount"]
        and b["total"] == p["total"]
        and b["total"] > 0.01
    )


def test_failed_demo_payment_releases_seats(viewer):
    client, _ = viewer
    show, seats, _, b = paid(client, transaction_success=False)
    assert b["status"] == "cancelled" and b["items"] == []
    assert (
        client.post(
            "/api/v1/bookings/holds",
            json={"showtime_id": show["id"], "seat_ids": seats},
        ).status_code
        == 201
    )


def test_no_unconfigured_webhook_can_confirm(viewer):
    client, _ = viewer
    assert (
        client.post(
            "/api/v1/payments/webhooks/stripe", json={"status": "paid"}
        ).status_code
        == 503
    )
    assert (
        client.post(
            "/api/v1/payments/webhooks/stripe", json={"status": "paid"}
        ).status_code
        == 503
    )
    assert client.get("/api/v1/me/tickets").json() == []


def test_ticket_single_scan_and_staff_permissions(viewer):
    client, _ = viewer
    _, _, _, b = paid(client)
    token = b["items"][0]["ticket_code"]
    scan_data = {"ticket_code": token, "showtime_id": b["showtime"]["id"]}
    assert (
        client.post("/api/v1/staff/tickets/validate", json=scan_data).status_code == 403
    )
    client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "TestPassword123!"},
    )
    assert (
        client.post("/api/v1/staff/tickets/validate", json=scan_data).status_code == 200
    )
    assert (
        client.post("/api/v1/staff/tickets/validate", json=scan_data).json()["reason"]
        == "already_used"
    )


def test_concurrent_claim_only_one_succeeds(viewer):
    client, factory = viewer
    show, seats = choose(client)
    with factory() as db:
        u = User(
            email="racer@example.com",
            name="Racer",
            password_hash=hash_password("TestPassword123!"),
        )
        db.add(u)
        db.commit()
        ids = [
            db.scalar(select(User.id).where(User.email == "viewer@example.com")),
            u.id,
        ]
    barrier = Barrier(2)

    def reserve(user_id):
        barrier.wait(timeout=10)
        with factory() as db:
            try:
                create_hold(
                    db, user_id, HoldInput(showtime_id=show["id"], seat_ids=seats)
                )
                db.commit()
                return 201
            except HTTPException as exc:
                db.rollback()
                return exc.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(reserve, ids)) == [201, 409]
    with factory() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(SeatClaim)
                .where(
                    SeatClaim.showtime_id == show["id"], SeatClaim.seat_id == seats[0]
                )
            )
            == 1
        )


def test_admin_create_movie_and_conflicting_screening(admin):
    client, _ = admin
    original = client.get("/api/v1/movies/1").json()
    payload = {**original, "slug": "test-film", "title": "Тестов филм"}
    created = client.post("/api/v1/admin/movies", json=payload)
    assert created.status_code == 201, created.text
    show = client.get("/api/v1/showtimes").json()[0]
    data = {
        "movie_id": created.json()["id"],
        "auditorium_id": show["auditorium_id"],
        "starts_at": show["starts_at"],
        "price": 12,
        "format": show["format"],
    }
    assert client.post("/api/v1/admin/showtimes", json=data).status_code == 409
    data["starts_at"] = (
        (utcnow() + timedelta(days=12)).replace(tzinfo=timezone.utc).isoformat()
    )
    assert client.post("/api/v1/admin/showtimes", json=data).status_code == 201
    assert client.get("/api/v1/admin/dashboard").json()["movies"] >= 16
    assert client.get("/api/v1/admin/audit-logs").json()


def test_admin_cannot_schedule_in_past_or_demote_self(admin):
    client, _ = admin
    show = client.get("/api/v1/showtimes").json()[0]
    data = {
        "movie_id": 1,
        "auditorium_id": show["auditorium_id"],
        "starts_at": (utcnow() - timedelta(days=1))
        .replace(tzinfo=timezone.utc)
        .isoformat(),
        "price": 12,
        "format": "2D",
    }
    assert client.post("/api/v1/admin/showtimes", json=data).status_code == 422
    me = client.get("/api/v1/me").json()
    assert (
        client.patch(
            "/api/v1/admin/users/" + str(me["id"]),
            json={"role": "user", "active": True},
        ).status_code
        == 409
    )


def test_profile_export_and_deletion_request(viewer):
    client, _ = viewer
    assert (
        client.patch("/api/v1/me", json={"name": "Ново име", "role": "admin"}).json()[
            "role"
        ]
        == "user"
    )
    assert client.get("/api/v1/me/export").json()["profile"]["name"] == "Ново име"
    assert client.delete("/api/v1/me").status_code == 200
    assert client.get("/api/v1/me").json()["deletion_requested"]


def test_password_change_invalidates_other_sessions(viewer):
    client, factory = viewer
    old = client.cookies.get("pukankov_session")
    assert (
        client.post(
            "/api/v1/me/password",
            json={"current_password": "wrong", "password": "DifferentPassword123"},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/me/password",
            json={
                "current_password": "TestPassword123!",
                "password": "DifferentPassword123",
            },
        ).status_code
        == 200
    )
    assert client.cookies.get("pukankov_session") != old
    assert (
        client.get("/api/v1/me", cookies={"pukankov_session": old}).status_code == 401
    )


def test_password_reset_does_not_claim_email_delivery(setup):
    client, _ = setup
    data = client.post(
        "/api/v1/auth/forgot-password", json={"email": "nobody@example.com"}
    ).json()
    assert data["email_configured"] is False
    assert (
        client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": "not-a-real-token-123456",
                "password": "DifferentPassword123",
            },
        ).status_code
        == 422
    )


def test_login_rate_limit(setup):
    client, _ = setup
    for _ in range(10):
        client.post(
            "/api/v1/auth/login",
            json={"email": "viewer@example.com", "password": "wrong"},
        )
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"email": "viewer@example.com", "password": "wrong"},
        ).status_code
        == 429
    )
