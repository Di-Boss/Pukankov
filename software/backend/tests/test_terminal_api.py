from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, func
from app.db import get_db, utcnow, Base
from app.main import app as website
from app.public_gateway import app as gateway
from app.models import Booking, Ticket, Payment, Hold, AuditLog
from test_diploma import device
from test_platform import choose


@pytest.fixture
def api(viewer):
    site, factory = viewer
    _, headers = device(factory, "kiosk")
    gateway.dependency_overrides[get_db] = website.dependency_overrides[get_db]
    try:
        with TestClient(gateway) as public:
            yield public, site, factory, headers
    finally:
        gateway.dependency_overrides.clear()


def reserve(api):
    public, site, _, headers = api
    show, seats = choose(site)
    result = public.post(
        "/api/v1/devices/bookings/holds",
        headers=headers,
        json={"showtime_id": show["id"], "seat_ids": seats},
    )
    assert result.status_code == 201
    return show, seats, result.json()


def test_public_api_is_device_only_and_has_no_card_schema(api):
    public, _, _, headers = api
    landing = public.get("/")
    assert landing.status_code == 200
    assert landing.json()["docs"] == "/api/docs"
    assert public.get(landing.json()["health"]).status_code == 200
    assert public.get("/api/v1/health").json()["payment_mode"] == "terminal_signal"
    assert public.get("/api/v1/devices/movies").status_code == 401
    assert public.get("/api/v1/devices/movies", headers=headers).status_code == 200
    for path in (
        "/admin",
        "/api/v1/admin/users",
        "/api/v1/me",
        "/pukankov.db",
        "/backend/pukankov.db",
    ):
        assert public.get(path, headers=headers).status_code == 404
    assert (
        public.post(
            "/api/v1/devices/payments/rfid", headers=headers, json={}
        ).status_code
        == 404
    )
    assert public.post("/api/v1/auth/register", json={}).status_code == 404
    schema = public.get("/api/openapi.json").json()["components"]["schemas"]
    assert "rfid_uid" not in schema["TerminalCheckoutInput"]["properties"]
    assert (
        "rfid_cards" not in Base.metadata.tables
        and "rfid_payments" not in Base.metadata.tables
    )


def test_movie_date_time_filters_and_shared_availability(api):
    public, site, factory, headers = api
    movies = public.get("/api/v1/devices/movies", headers=headers).json()
    assert movies and all(
        set(m) == {"id", "title", "duration", "age", "year"} for m in movies
    )
    movie = movies[0]
    listed = public.get(
        f'/api/v1/devices/showtimes?movie_id={movie["id"]}&limit=1', headers=headers
    )
    assert int(listed.headers["x-total-count"]) >= 1
    show = listed.json()[0]
    filtered = public.get(
        "/api/v1/devices/showtimes",
        headers=headers,
        params={
            "movie_id": movie["id"],
            "date": show["date"],
            "from_hour": int(show["time"][:2]),
            "to_hour": int(show["time"][:2]) + 1,
        },
    ).json()
    assert filtered and all(
        s["movie_id"] == movie["id"] and s["date"] == show["date"] for s in filtered
    )
    seats = public.get(
        f'/api/v1/devices/showtimes/{show["id"]}/seats', headers=headers
    ).json()["seats"]
    assert show["available_seats"] == sum(s["status"] == "available" for s in seats)
    selected = next(s["id"] for s in seats if s["status"] == "available")
    hold = public.post(
        "/api/v1/devices/bookings/holds",
        headers=headers,
        json={"showtime_id": show["id"], "seat_ids": [selected]},
    ).json()
    assert (
        next(
            s
            for s in site.get(f'/api/v1/showtimes/{show["id"]}/seats').json()["seats"]
            if s["id"] == selected
        )["status"]
        == "held"
    )
    with factory() as db:
        db.get(Hold, hold["id"]).expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
    after = public.get(
        f'/api/v1/devices/showtimes?movie_id={movie["id"]}', headers=headers
    ).json()
    assert (
        next(s for s in after if s["id"] == show["id"])["available_seats"]
        == show["available_seats"]
    )
    assert (
        public.get("/api/v1/devices/showtimes?date=bad", headers=headers).status_code
        == 422
    )
    assert (
        public.get(
            "/api/v1/devices/showtimes?from_hour=12&to_hour=10", headers=headers
        ).status_code
        == 422
    )


def test_gate_validates_code_without_showtime_and_only_once(api):
    public, site, factory, headers = api
    _, validator = device(factory, "validator")
    receipts = []
    shows = site.get("/api/v1/showtimes").json()[:2]
    for show in shows:
        available = site.get(f'/api/v1/showtimes/{show["id"]}/seats').json()["seats"]
        seat = next(s["id"] for s in available if s["status"] == "available")
        hold = public.post("/api/v1/devices/bookings/holds", headers=headers,
                           json={"showtime_id": show["id"], "seat_ids": [seat]}).json()
        receipt = public.post("/api/v1/devices/payments/checkout", headers=headers,
                              json={"hold_id": hold["id"], "payment_success": True}).json()
        receipts.append(receipt)
    for receipt in receipts:
        payload = {"ticket_code": receipt["ticket_code"]}
        assert public.post("/api/validator/validate", headers=headers, json=payload).status_code == 403
        response = public.post("/api/validator/validate", headers=validator, json=payload)
        assert response.status_code == 200 and response.json()["valid"] is True
        assert response.json()["showtime_id"] == receipt["showtime_id"]
        assert public.post("/api/validator/validate", headers=validator, json=payload).json()["reason"] == "already_used"
    assert public.post("/api/validator/validate", headers=validator, json={"ticket_code": "000000"}).json()["reason"] == "invalid_code"
    assert public.post("/api/validator/validate", headers=validator, json={"ticket_code": "12345"}).status_code == 422


def test_code_only_gate_consumption_is_atomic(api):
    public, _, factory, headers = api
    _, _, hold = reserve(api)
    receipt = public.post("/api/v1/devices/payments/checkout", headers=headers,
                          json={"hold_id": hold["id"], "payment_success": True}).json()
    from app.models import Device
    from app.services.tickets import validate_ticket
    _, validator_headers = device(factory, "validator")
    from app.core.security import digest
    with factory() as db:
        validator_device = db.scalar(select(Device).where(Device.key_hash == digest(validator_headers["Authorization"].split()[1])))
        actor_id = validator_device.user_id
    barrier = Barrier(2)
    def consume(_):
        with factory() as db:
            barrier.wait(timeout=10)
            result = validate_ticket(db, receipt["ticket_code"], None, actor_id)
            db.commit()
            return result["valid"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(consume, range(2))) == [False, True]


def test_eight_seats_one_payment_and_eight_distinct_codes(api):
    public, site, factory, headers = api
    show, seat_ids = choose(site, 9)
    assert len(seat_ids) == 9
    rejected = public.post(
        "/api/v1/devices/bookings/holds", headers=headers,
        json={"showtime_id": show["id"], "seat_ids": seat_ids},
    )
    assert rejected.status_code == 422
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(Hold)) == 0
    hold_response = public.post(
        "/api/v1/devices/bookings/holds", headers=headers,
        json={"showtime_id": show["id"], "seat_ids": seat_ids[:8]},
    )
    assert hold_response.status_code == 201
    hold = hold_response.json()
    payload = {"hold_id": hold["id"], "payment_success": True}
    response = public.post("/api/v1/devices/payments/checkout", headers=headers, json=payload)
    assert response.status_code == 200, response.text
    receipt = response.json()
    assert receipt["success"] and receipt["ticket_code"] is None
    assert receipt["amount"] == hold["total"]
    assert len(receipt["tickets"]) == 8
    codes = {ticket["ticket_code"] for ticket in receipt["tickets"]}
    assert len(codes) == 8 and all(len(code) == 6 and code.isdigit() for code in codes)
    assert len({ticket["seat"] for ticket in receipt["tickets"]}) == 8
    assert public.post("/api/v1/devices/payments/checkout", headers=headers, json=payload).json() == receipt
    assert public.get(f'/api/v1/devices/bookings/{receipt["booking_id"]}', headers=headers).json() == receipt
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(Payment)) == 1
        assert db.scalar(select(func.count()).select_from(Ticket)) == 8


def test_success_signal_issues_tickets_once_and_receipt_tracks_use(api):
    public, site, factory, headers = api
    show, seats, hold = reserve(api)
    data = {"hold_id": hold["id"], "payment_success": True}
    first = public.post("/api/v1/devices/payments/checkout", headers=headers, json=data)
    assert first.status_code == 200, first.text
    result = first.json()
    assert result["success"] is True and result["status"] == "confirmed"
    assert len(result["ticket_code"]) == 6 and result["amount"] == hold["total"]
    assert result["payment_method"] == "terminal_signal"
    assert (
        public.post(
            "/api/v1/devices/payments/checkout", headers=headers, json=data
        ).json()
        == result
    )
    # A contradictory retry must not cancel an already successful transaction.
    assert (
        public.post(
            "/api/v1/devices/payments/checkout",
            headers=headers,
            json={**data, "payment_success": False},
        ).json()
        == result
    )
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(Payment)) == 1
        assert db.scalar(select(Payment)).status == "terminal_success"
        assert (
            db.scalar(
                select(func.count())
                .select_from(AuditLog)
                .where(AuditLog.action == "terminal.payment_success")
            )
            == 1
        )
    _, validator = device(factory, "validator")
    assert (
        public.post(
            "/api/validator/validate",
            headers=validator,
            json={"ticket_code": result["ticket_code"], "showtime_id": show["id"]},
        ).json()["valid"]
        is True
    )
    assert (
        public.get(
            f'/api/v1/devices/bookings/{result["booking_id"]}', headers=headers
        ).json()["tickets"][0]["status"]
        == "used"
    )


def test_failed_signal_issues_no_ticket_and_frees_seat(api):
    public, site, factory, headers = api
    show, seats, hold = reserve(api)
    data = {"hold_id": hold["id"], "payment_success": False}
    denied = public.post(
        "/api/v1/devices/payments/checkout", headers=headers, json=data
    )
    assert denied.status_code == 200 and denied.json()["success"] is False
    assert denied.json()["status"] == "cancelled" and denied.json()["tickets"] == []
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(Ticket)) == 0
        assert db.scalar(select(Payment)).status == "failed"
    assert (
        public.post(
            "/api/v1/devices/payments/checkout",
            headers=headers,
            json={**data, "payment_success": True},
        ).json()["success"]
        is False
    )
    assert (
        site.post(
            "/api/v1/bookings/holds",
            json={"showtime_id": show["id"], "seat_ids": seats},
        ).status_code
        == 201
    )


@pytest.mark.parametrize(
    "extra", [{"rfid_uid": "DEADBEEF"}, {"amount": 0}, {"transaction_success": True}]
)
def test_card_data_and_untrusted_amount_are_not_accepted(api, extra):
    public, _, _, headers = api
    _, _, hold = reserve(api)
    assert (
        public.post(
            "/api/v1/devices/payments/checkout",
            headers=headers,
            json={"hold_id": hold["id"], "payment_success": True, **extra},
        ).status_code
        == 422
    )


@pytest.mark.parametrize("flag", ["true", 1, None])
def test_payment_success_must_be_a_json_boolean(api, flag):
    public, _, _, headers = api
    _, _, hold = reserve(api)
    assert (
        public.post(
            "/api/v1/devices/payments/checkout",
            headers=headers,
            json={"hold_id": hold["id"], "payment_success": flag},
        ).status_code
        == 422
    )


def test_other_terminal_and_validator_cannot_confirm_or_cancel_hold(api):
    public, _, factory, headers = api
    _, _, hold = reserve(api)
    _, other = device(factory, "kiosk")
    _, validator = device(factory, "validator")
    data = {"hold_id": hold["id"], "payment_success": True}
    assert (
        public.post(
            "/api/v1/devices/payments/checkout", headers=other, json=data
        ).status_code
        == 404
    )
    assert (
        public.delete(
            f'/api/v1/devices/bookings/holds/{hold["id"]}', headers=other
        ).status_code
        == 404
    )
    assert (
        public.post(
            "/api/v1/devices/payments/checkout", headers=validator, json=data
        ).status_code
        == 403
    )
    assert (
        public.delete(
            f'/api/v1/devices/bookings/holds/{hold["id"]}', headers=headers
        ).json()["status"]
        == "cancelled"
    )
    assert (
        public.post(
            "/api/v1/devices/payments/checkout", headers=headers, json=data
        ).status_code
        == 409
    )


def test_concurrent_terminal_signals_issue_one_order(api):
    public, _, factory, headers = api
    _, _, hold = reserve(api)
    barrier = Barrier(2)

    def pay(_):
        barrier.wait(timeout=10)
        response = public.post(
            "/api/v1/devices/payments/checkout",
            headers=headers,
            json={"hold_id": hold["id"], "payment_success": True},
        )
        assert response.status_code == 200, response.text
        return response.json()["booking_id"]

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert len(set(pool.map(pay, range(2)))) == 1
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(Booking)) == 1
        assert db.scalar(select(func.count()).select_from(Ticket)) == 1


def test_expired_hold_and_missing_success_are_rejected(api):
    public, _, factory, headers = api
    _, _, hold = reserve(api)
    assert (
        public.post(
            "/api/v1/devices/payments/checkout",
            headers=headers,
            json={"hold_id": hold["id"]},
        ).status_code
        == 422
    )
    with factory() as db:
        db.get(Hold, hold["id"]).expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
    assert (
        public.post(
            "/api/v1/devices/payments/checkout",
            headers=headers,
            json={"hold_id": hold["id"], "payment_success": True},
        ).status_code
        == 409
    )


def test_terminal_payment_attempt_limit(api):
    public, _, _, headers = api
    _, _, hold = reserve(api)
    data = {"hold_id": hold["id"], "payment_success": False}
    for _ in range(20):
        assert (
            public.post(
                "/api/v1/devices/payments/checkout", headers=headers, json=data
            ).status_code
            == 200
        )
    assert (
        public.post(
            "/api/v1/devices/payments/checkout", headers=headers, json=data
        ).status_code
        == 429
    )
