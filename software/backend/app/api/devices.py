"""One API for the website, a Wokwi kiosk and a Raspberry Pi entry validator."""

from types import SimpleNamespace

from fastapi import APIRouter, Depends, HTTPException, Request, Query, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select, delete, func
from sqlalchemy.orm import Session
from ..db import get_db, utcnow
from ..models import (
    Device,
    Showtime,
    Movie,
    Seat,
    SeatClaim,
    Hold,
    Booking,
    Payment,
    AuditLog,
)
from ..core.security import digest, limiter
from ..schemas import HoldInput, TerminalCheckoutInput, DeviceTicketScan
from ..services.reservations import (
    create_hold,
    hold_dict,
    owned_hold,
    seats_dict,
    checkout,
)
from ..services.serializers import booking_dict
from ..services.tickets import validate_ticket
from .public import showtimes as public_showtimes

router = APIRouter(prefix="/api/v1/devices", tags=["Devices"])
validator_router = APIRouter(prefix="/api/validator", tags=["Validator"])
bearer = HTTPBearer(auto_error=False)


def current_device(
    request: Request,
    auth: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
):
    limiter.check(("device-auth", request.client.host), limit=120, window=60)
    device = (
        db.scalar(select(Device).where(Device.key_hash == digest(auth.credentials)))
        if auth
        else None
    )
    if not device or not device.active:
        raise HTTPException(401, "Невалиден или отзован ключ на устройство.")
    return device


def kiosk(device: Device = Depends(current_device)):
    if device.role != "kiosk":
        raise HTTPException(403, "Устройството няма права за продажба на билети.")
    return device


def validator(device: Device = Depends(current_device)):
    if device.role != "validator":
        raise HTTPException(403, "Устройството няма права за входен контрол.")
    return device


def scoped_show(db, device, showtime_id):
    show = db.get(Showtime, showtime_id)
    if not show or not db.get(Movie, show.movie_id).in_catalog:
        raise HTTPException(404, "Прожекцията не е намерена.")
    if device.auditorium_id is not None and show.auditorium_id != device.auditorium_id:
        raise HTTPException(403, "Прожекцията е извън залата на устройството.")
    return show


@router.get("/showtimes")
def shows(
    response: Response,
    movie_id: int | None = Query(None, gt=0),
    cinema_id: int | None = Query(None, gt=0),
    date: str = "",
    from_hour: int = Query(0, ge=0, le=23),
    to_hour: int = Query(24, ge=1, le=24),
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    device: Device = Depends(current_device),
    db: Session = Depends(get_db),
):
    if to_hour <= from_hour:
        raise HTTPException(422, "Крайният час трябва да е след началния.")
    items = public_showtimes(
        movie_id=movie_id,
        cinema_id=cinema_id,
        date=date,
        from_hour=from_hour,
        to_hour=to_hour,
        db=db,
    )
    items = [
        s
        for s in items
        if device.auditorium_id is None or s["auditorium_id"] == device.auditorium_id
    ]
    response.headers["X-Total-Count"] = str(len(items))
    items = items[offset : offset + limit]
    show_ids = [s["id"] for s in items]
    auditorium_ids = {s["auditorium_id"] for s in items}
    totals = dict(
        db.execute(
            select(Seat.auditorium_id, func.count())
            .where(Seat.auditorium_id.in_(auditorium_ids), Seat.active.is_(True))
            .group_by(Seat.auditorium_id)
        ).all()
    )
    sold = dict(
        db.execute(
            select(SeatClaim.showtime_id, func.count())
            .join(Seat, Seat.id == SeatClaim.seat_id)
            .where(
                SeatClaim.showtime_id.in_(show_ids),
                SeatClaim.booking_id.is_not(None),
                Seat.active.is_(True),
            )
            .group_by(SeatClaim.showtime_id)
        ).all()
    )
    held = dict(
        db.execute(
            select(SeatClaim.showtime_id, func.count())
            .join(Seat, Seat.id == SeatClaim.seat_id)
            .join(Hold, Hold.id == SeatClaim.hold_id)
            .where(
                SeatClaim.showtime_id.in_(show_ids),
                SeatClaim.booking_id.is_(None),
                Seat.active.is_(True),
                Hold.status == "active",
                Hold.expires_at > utcnow(),
            )
            .group_by(SeatClaim.showtime_id)
        ).all()
    )
    return [
        {
            "id": s["id"],
            "movie_id": s["movie_id"],
            "movie_title": s["movie"]["title"],
            "cinema_id": s["cinema"]["id"],
            "cinema": s["cinema"]["name"],
            "city": s["cinema"]["city"],
            "auditorium_id": s["auditorium_id"],
            "auditorium": s["auditorium"],
            "date": s["date"],
            "time": s["time"],
            "starts_at": s["starts_at"],
            "format": s["format"],
            "price": s["price"],
            "currency": "EUR",
            "timezone": "Europe/Sofia",
            "available_seats": max(
                0,
                totals.get(s["auditorium_id"], 0)
                - sold.get(s["id"], 0)
                - held.get(s["id"], 0),
            ),
            "held_seats": held.get(s["id"], 0),
            "sold_seats": sold.get(s["id"], 0),
        }
        for s in items
    ]


@router.get("/movies")
def movies(
    q: str = Query("", max_length=100),
    date: str = "",
    cinema_id: int | None = Query(None, gt=0),
    device: Device = Depends(current_device),
    db: Session = Depends(get_db),
):
    items = public_showtimes(
        movie_id=None, cinema_id=cinema_id, date=date, from_hour=0, to_hour=24, db=db
    )
    movie_ids = {
        s["movie_id"]
        for s in items
        if device.auditorium_id is None or s["auditorium_id"] == device.auditorium_id
    }
    return [
        {
            "id": m.id,
            "title": m.title,
            "duration": m.duration,
            "age": m.age,
            "year": m.year,
        }
        for m in db.scalars(
            select(Movie)
            .where(Movie.id.in_(movie_ids), Movie.in_catalog.is_(True))
            .order_by(Movie.title)
        ).all()
        if not q or q.casefold() in (m.title + " " + m.original_title).casefold()
    ]


@router.get("/showtimes/{showtime_id}/seats")
def device_seats(
    showtime_id: int, device: Device = Depends(kiosk), db: Session = Depends(get_db)
):
    return seats_dict(db, scoped_show(db, device, showtime_id))


@router.post("/bookings/holds", status_code=201)
def device_hold(
    data: HoldInput, device: Device = Depends(kiosk), db: Session = Depends(get_db)
):
    show = scoped_show(db, device, data.showtime_id)
    hold = create_hold(db, device.user_id, data)
    return hold_dict(db, hold, show)


@router.post("/payments/checkout")
def device_checkout(
    data: TerminalCheckoutInput,
    device: Device = Depends(kiosk),
    db: Session = Depends(get_db),
):
    limiter.check(("device-payment", device.id), limit=20, window=60)
    hold, _ = owned_hold(db, data.hold_id, device.user_id)
    scoped_show(db, device, hold.showtime_id)
    b = checkout(
        db,
        device.user_id,
        SimpleNamespace(
            hold_id=data.hold_id,
            promo_code=data.promo_code,
            terms=data.terms,
            transaction_success=data.payment_success,
        ),
        provider="terminal_signal",
    )
    if not db.scalar(
        select(AuditLog.id).where(
            AuditLog.object_id == b.id,
            AuditLog.action.in_(
                ("terminal.payment_success", "terminal.payment_failed")
            ),
        )
    ):
        db.add(
            AuditLog(
                user_id=device.user_id,
                action=(
                    "terminal.payment_success"
                    if b.status == "confirmed"
                    else "terminal.payment_failed"
                ),
                object_id=b.id,
            )
        )
    return receipt(db, b)


def receipt(db, b):
    result = booking_dict(db, b)
    payment = db.scalar(select(Payment).where(Payment.booking_id == b.id))
    return {
        "success": b.status == "confirmed",
        "booking_id": b.id,
        "status": b.status,
        "movie": result["showtime"]["movie"]["title"],
        "showtime_id": b.showtime_id,
        "showtime": result["showtime"]["time"],
        "date": result["showtime"]["date"],
        "starts_at": result["showtime"]["starts_at"],
        "amount": float(b.total),
        "currency": b.currency,
        "payment_method": payment.provider if payment else None,
        "is_simulation": True,
        "tickets": [
            {
                "ticket_code": i["ticket_code"],
                "seat": f"{i['row']}{i['number']}",
                "status": "used" if i["used_at"] else "valid",
            }
            for i in result["items"]
        ],
        "ticket_code": (
            result["items"][0]["ticket_code"] if len(result["items"]) == 1 else None
        ),
    }


@router.get("/bookings/holds/{hold_id}")
def device_get_hold(
    hold_id: str, device: Device = Depends(kiosk), db: Session = Depends(get_db)
):
    hold, show = owned_hold(db, hold_id, device.user_id)
    scoped_show(db, device, show.id)
    return hold_dict(db, hold, show)


@router.delete("/bookings/holds/{hold_id}")
def device_cancel_hold(
    hold_id: str, device: Device = Depends(kiosk), db: Session = Depends(get_db)
):
    hold, show = owned_hold(db, hold_id, device.user_id)
    scoped_show(db, device, show.id)
    if hold.status == "active":
        hold.status = "cancelled"
        db.execute(
            delete(SeatClaim).where(
                SeatClaim.hold_id == hold.id, SeatClaim.booking_id.is_(None)
            )
        )
    return {"status": hold.status, "message": "Задържаните места са освободени."}


@router.get("/bookings/{booking_id}")
def device_receipt(
    booking_id: str, device: Device = Depends(kiosk), db: Session = Depends(get_db)
):
    booking = db.get(Booking, booking_id)
    if not booking or booking.user_id != device.user_id:
        raise HTTPException(404, "Поръчката не е намерена.")
    scoped_show(db, device, booking.showtime_id)
    return receipt(db, booking)


@router.post("/tickets/validate")
@validator_router.post("/validate")
def device_validate(
    data: DeviceTicketScan, device: Device = Depends(validator), db: Session = Depends(get_db)
):
    limiter.check(("device-code", device.id), limit=30, window=60)
    return validate_ticket(
        db, data.ticket_code, data.showtime_id, device.user_id, device.auditorium_id
    )
