import secrets
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from fastapi import HTTPException
from sqlalchemy import select, delete, func
from ..db import utcnow
from ..models import (
    Showtime,
    Hold,
    Seat,
    SeatClaim,
    Booking,
    Ticket,
    Payment,
    BookingEvent,
    Promotion,
    Redemption,
)
from ..core.config import settings
from ..core.security import digest
from .tickets import issue_ticket
from .serializers import showtime_dict, iso


def lock_showtime(db, showtime_id):
    show = db.scalar(
        select(Showtime).where(Showtime.id == showtime_id).with_for_update()
    )
    if not show:
        raise HTTPException(404, "Прожекцията не е намерена.")
    return show


def expire_holds(db, showtime_id):
    expired = db.scalars(
        select(Hold)
        .where(
            Hold.showtime_id == showtime_id,
            Hold.status == "active",
            Hold.expires_at <= utcnow(),
        )
        .with_for_update()
    ).all()
    for h in expired:
        db.execute(
            delete(SeatClaim).where(
                SeatClaim.hold_id == h.id, SeatClaim.booking_id.is_(None)
            )
        )
        h.status = "expired"
    db.flush()


def owned_hold(db, hold_id, user_id):
    # Lock the screening first everywhere to keep lock order consistent.
    candidate = db.get(Hold, hold_id)
    if not candidate or candidate.user_id != user_id:
        raise HTTPException(404, "Резервацията не е намерена.")
    show = lock_showtime(db, candidate.showtime_id)
    expire_holds(db, show.id)
    db.refresh(candidate)
    return candidate, show


def active_hold(db, hold_id, user_id):
    hold, show = owned_hold(db, hold_id, user_id)
    if hold.status != "active" or hold.expires_at <= utcnow():
        raise HTTPException(
            409, "Времето за резервация изтече. Изберете местата отново."
        )
    if show.cancelled or show.starts_at <= utcnow():
        raise HTTPException(409, "Прожекцията вече не е достъпна.")
    return hold, show


def seats_dict(db, show):
    lock_showtime(db, show.id)
    expire_holds(db, show.id)
    claims = {
        c.seat_id: c
        for c in db.scalars(
            select(SeatClaim).where(SeatClaim.showtime_id == show.id)
        ).all()
    }
    seats = db.scalars(
        select(Seat)
        .where(Seat.auditorium_id == show.auditorium_id)
        .order_by(Seat.row, Seat.number)
    ).all()
    return {
        "showtime": showtime_dict(db, show),
        "max_seats": settings.max_seats,
        "seats": [
            {
                "id": s.id,
                "row": s.row,
                "number": s.number,
                "category": s.category,
                "accessible": s.accessible,
                "price": float(show.price + s.surcharge),
                "status": (
                    "unavailable"
                    if not s.active
                    else (
                        "sold"
                        if s.id in claims and claims[s.id].booking_id
                        else "held" if s.id in claims else "available"
                    )
                ),
            }
            for s in seats
        ],
    }


def create_hold(db, user_id, data):
    show = lock_showtime(db, data.showtime_id)
    if show.cancelled or show.starts_at <= utcnow():
        raise HTTPException(409, "Тази прожекция вече не е достъпна.")
    if len(data.seat_ids) > settings.max_seats:
        raise HTTPException(422, f"Можете да изберете до {settings.max_seats} места.")
    expire_holds(db, show.id)
    seats = db.scalars(
        select(Seat).where(
            Seat.id.in_(data.seat_ids),
            Seat.auditorium_id == show.auditorium_id,
            Seat.active.is_(True),
        )
    ).all()
    if len(seats) != len(data.seat_ids):
        raise HTTPException(422, "Невалидни или недостъпни места.")
    if db.scalar(
        select(SeatClaim.id)
        .where(SeatClaim.showtime_id == show.id, SeatClaim.seat_id.in_(data.seat_ids))
        .limit(1)
    ):
        raise HTTPException(409, "Някое от местата вече е заето. Изберете други места.")
    if (
        db.scalar(
            select(func.count())
            .select_from(Hold)
            .where(
                Hold.user_id == user_id,
                Hold.status == "active",
                Hold.expires_at > utcnow(),
            )
        )
        >= 3
    ):
        raise HTTPException(
            429, "Имате три активни резервации. Завършете или откажете някоя от тях."
        )
    hold = Hold(
        id=secrets.token_urlsafe(18),
        user_id=user_id,
        showtime_id=show.id,
        expires_at=utcnow() + timedelta(seconds=settings.hold_seconds),
    )
    db.add(hold)
    db.flush()
    for seat in seats:
        db.add(
            SeatClaim(
                showtime_id=show.id,
                seat_id=seat.id,
                hold_id=hold.id,
                price=show.price + seat.surcharge,
            )
        )
    db.flush()
    return hold


def hold_dict(db, hold, show):
    claims = db.scalars(select(SeatClaim).where(SeatClaim.hold_id == hold.id)).all()
    items = []
    for c in claims:
        s = db.get(Seat, c.seat_id)
        items.append(
            {
                "id": s.id,
                "row": s.row,
                "number": s.number,
                "category": s.category,
                "price": float(c.price),
            }
        )
    return {
        "id": hold.id,
        "expires_at": iso(hold.expires_at),
        "server_time": iso(utcnow()),
        "status": hold.status,
        "showtime": showtime_dict(db, show),
        "items": items,
        "total": float(sum((c.price for c in claims), Decimal(0))),
    }


def validate_promotion(db, code, user_id, subtotal):
    promo = db.scalar(
        select(Promotion)
        .where(Promotion.code == code.strip().upper())
        .with_for_update()
    )
    now = utcnow()
    if (
        not promo
        or not promo.active
        or promo.starts_at > now
        or promo.ends_at <= now
        or subtotal < promo.minimum
    ):
        raise HTTPException(
            422, "Промокодът е невалиден, изтекъл или минималната сума не е достигната."
        )
    total_uses = db.scalar(
        select(func.count())
        .select_from(Redemption)
        .where(Redemption.promotion_id == promo.id)
    )
    user_uses = db.scalar(
        select(func.count())
        .select_from(Redemption)
        .where(Redemption.promotion_id == promo.id, Redemption.user_id == user_id)
    )
    if total_uses >= promo.max_uses or user_uses >= promo.per_user:
        raise HTTPException(422, "Лимитът за използване на този промокод е достигнат.")
    return promo, (subtotal * Decimal(promo.percent) / 100).quantize(
        Decimal(".01"), rounding=ROUND_HALF_UP
    )


def checkout(db, user_id, data, *, provider="card_simulator"):
    if provider not in ("card_simulator", "terminal_signal"):
        raise ValueError("Unsupported internal payment provider")
    if provider == "card_simulator" and settings.payment_mode not in (
        "simulation",
        "demo",
    ):
        raise HTTPException(
            503, "Реалните плащания не са конфигурирани. Не е извършено плащане."
        )
    if not data.terms:
        raise HTTPException(422, "Приемете условията за демонстрационна поръчка.")
    hold, show = owned_hold(db, data.hold_id, user_id)
    # Idempotent retries return the original order, never duplicate tickets.
    existing = db.scalar(select(Booking).where(Booking.hold_id == hold.id))
    if existing:
        return existing
    if (
        hold.status != "active"
        or hold.expires_at <= utcnow()
        or show.cancelled
        or show.starts_at <= utcnow()
    ):
        raise HTTPException(409, "Резервацията е изтекла или прожекцията е отменена.")
    claims = db.scalars(select(SeatClaim).where(SeatClaim.hold_id == hold.id)).all()
    if not claims:
        raise HTTPException(409, "Няма задържани места.")
    subtotal = sum((c.price for c in claims), Decimal(0))
    promo, discount = (
        validate_promotion(db, data.promo_code, user_id, subtotal)
        if data.promo_code.strip()
        else (None, Decimal(0))
    )
    b = Booking(
        id="PK-" + secrets.token_hex(6).upper(),
        user_id=user_id,
        hold_id=hold.id,
        showtime_id=show.id,
        total=subtotal - discount,
        discount=discount,
        status="pending",
        is_demo=True,
    )
    db.add(b)
    db.flush()
    db.add(BookingEvent(booking_id=b.id, status="pending"))
    db.add(BookingEvent(booking_id=b.id, status="awaiting_payment"))
    if not data.transaction_success:
        b.status = "cancelled"
        hold.status = "cancelled"
        db.add(
            Payment(
                booking_id=b.id,
                amount=b.total,
                status="failed",
                provider=provider,
            )
        )
        db.add(BookingEvent(booking_id=b.id, status="cancelled"))
        db.execute(delete(SeatClaim).where(SeatClaim.hold_id == hold.id))
    else:
        # The demo provider is server-side and never handles bank card information.
        b.status = "confirmed"
        hold.status = "completed"
        db.add(
            Payment(
                booking_id=b.id,
                amount=b.total,
                status=(
                    "terminal_success"
                    if provider == "terminal_signal"
                    else "simulated_success"
                ),
                provider=provider,
            )
        )
        db.add(BookingEvent(booking_id=b.id, status="confirmed"))
        for claim in claims:
            claim.booking_id = b.id
            issue_ticket(db, b.id, claim.id)
        if promo:
            db.add(Redemption(promotion_id=promo.id, user_id=user_id, booking_id=b.id))
    db.flush()
    return b
