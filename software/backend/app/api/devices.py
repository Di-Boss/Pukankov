"""One API for the website, a Wokwi kiosk and a Raspberry Pi entry validator."""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import Device, Showtime, Movie
from ..core.security import digest, limiter
from ..schemas import HoldInput, CheckoutInput, TicketScan
from ..services.reservations import create_hold, hold_dict, checkout, seats_dict
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
def shows(device: Device = Depends(current_device), db: Session = Depends(get_db)):
    items = public_showtimes(
        movie_id=None, cinema_id=None, date="", from_hour=0, to_hour=24, db=db
    )
    return [
        s
        for s in items
        if device.auditorium_id is None or s["auditorium_id"] == device.auditorium_id
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
    data: CheckoutInput, device: Device = Depends(kiosk), db: Session = Depends(get_db)
):
    b = checkout(db, device.user_id, data)
    # Owner checks in checkout ensure one terminal cannot use another terminal's hold.
    result = booking_dict(db, b)
    return {
        "success": b.status == "confirmed",
        "booking_id": b.id,
        "status": b.status,
        "movie": result["showtime"]["movie"]["title"],
        "showtime": result["showtime"]["time"],
        "tickets": [
            {
                "ticket_code": i["ticket_code"],
                "seat": f"{i['row']}{i['number']}",
                "status": "valid",
            }
            for i in result["items"]
        ],
        "ticket_code": (
            result["items"][0]["ticket_code"] if len(result["items"]) == 1 else None
        ),
    }


@router.post("/tickets/validate")
@validator_router.post("/validate")
def device_validate(
    data: TicketScan, device: Device = Depends(validator), db: Session = Depends(get_db)
):
    limiter.check(("device-code", device.id), limit=30, window=60)
    return validate_ticket(
        db, data.ticket_code, data.showtime_id, device.user_id, device.auditorium_id
    )
