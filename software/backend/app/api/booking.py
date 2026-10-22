from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, delete
from sqlalchemy.orm import Session
from ..db import get_db, utcnow
from ..models import User, Showtime, SeatClaim, Booking, Ticket, AuditLog
from ..schemas import HoldInput, CheckoutInput, PromoInput, TicketScan
from ..core.security import current_user, staff_user, digest
from ..services.reservations import (
    create_hold,
    owned_hold,
    hold_dict,
    active_hold,
    validate_promotion,
    checkout,
)
from ..services.serializers import booking_dict
from ..services.tickets import validate_ticket
from ..core.security import limiter
from fastapi import Request

router = APIRouter(prefix="/api/v1")


@router.post("/bookings/holds", status_code=201)
def hold(
    data: HoldInput, u: User = Depends(current_user), db: Session = Depends(get_db)
):
    h = create_hold(db, u.id, data)
    return hold_dict(db, h, db.get(Showtime, h.showtime_id))


@router.get("/bookings/holds/{hold_id}")
def get_hold(
    hold_id: str, u: User = Depends(current_user), db: Session = Depends(get_db)
):
    h, s = owned_hold(db, hold_id, u.id)
    return hold_dict(db, h, s)


@router.delete("/bookings/holds/{hold_id}")
def cancel_hold(
    hold_id: str, u: User = Depends(current_user), db: Session = Depends(get_db)
):
    h, _ = owned_hold(db, hold_id, u.id)
    if h.status == "active":
        h.status = "cancelled"
        db.execute(
            delete(SeatClaim).where(
                SeatClaim.hold_id == h.id, SeatClaim.booking_id.is_(None)
            )
        )
    return {"message": "Задържаните места са освободени."}


@router.post("/promotions/validate")
def promo(
    data: PromoInput, u: User = Depends(current_user), db: Session = Depends(get_db)
):
    h, s = active_hold(db, data.hold_id, u.id)
    from decimal import Decimal

    total = sum(
        (
            c.price
            for c in db.scalars(
                select(SeatClaim).where(SeatClaim.hold_id == h.id)
            ).all()
        ),
        Decimal(0),
    )
    p, d = validate_promotion(db, data.code, u.id, total)
    return {"code": p.code, "discount": float(d), "total": float(total - d)}


@router.post("/payments/checkout")
def pay(
    data: CheckoutInput, u: User = Depends(current_user), db: Session = Depends(get_db)
):
    b = checkout(db, u.id, data)
    return booking_dict(db, b)


@router.post("/payments/webhooks/{provider}")
def webhook(provider: str):
    # Fail closed: no real payment adapter or webhook can confirm tickets.
    raise HTTPException(503, "Този платежен доставчик не е конфигуриран.")


@router.get("/bookings/{booking_id}")
def get_booking(
    booking_id: str, u: User = Depends(current_user), db: Session = Depends(get_db)
):
    b = db.get(Booking, booking_id)
    if not b or b.user_id != u.id:
        raise HTTPException(404, "Поръчката не е намерена.")
    return booking_dict(db, b)


@router.get("/me/bookings")
@router.get("/me/tickets")
def my_bookings(u: User = Depends(current_user), db: Session = Depends(get_db)):
    return [
        booking_dict(db, b)
        for b in db.scalars(
            select(Booking)
            .where(Booking.user_id == u.id)
            .order_by(Booking.created_at.desc())
        ).all()
    ]


@router.post("/staff/tickets/validate")
def scan(
    data: TicketScan,
    request: Request,
    u: User = Depends(staff_user),
    db: Session = Depends(get_db),
):
    limiter.check(("staff-code", u.id), limit=30, window=60)
    return validate_ticket(db, data.ticket_code, data.showtime_id, u.id)
