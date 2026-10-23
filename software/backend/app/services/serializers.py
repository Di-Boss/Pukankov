from zoneinfo import ZoneInfo
from datetime import timezone
from sqlalchemy import select
from ..models import (
    Movie,
    Showtime,
    Cinema,
    Auditorium,
    Seat,
    SeatClaim,
    Ticket,
    BookingEvent,
)


def iso(dt):
    return dt.replace(tzinfo=timezone.utc).isoformat() if dt else None


def movie_dict(m):
    return {
        c.name: (
            float(getattr(m, c.name))
            if c.name == "rating"
            else (
                iso(getattr(m, c.name))
                if c.name in ("created_at", "updated_at")
                else getattr(m, c.name)
            )
        )
        for c in Movie.__table__.columns
    }


def cinema_dict(c):
    return {col.name: getattr(c, col.name) for col in Cinema.__table__.columns}


def showtime_dict(db, s):
    a = db.get(Auditorium, s.auditorium_id)
    c = db.get(Cinema, a.cinema_id)
    m = db.get(Movie, s.movie_id)
    local = s.starts_at.replace(tzinfo=timezone.utc).astimezone(
        ZoneInfo("Europe/Sofia")
    )
    return {
        "id": s.id,
        "movie_id": s.movie_id,
        "movie": movie_dict(m),
        "cinema": cinema_dict(c),
        "auditorium_id": a.id,
        "auditorium": a.name,
        "starts_at": iso(s.starts_at),
        "date": local.strftime("%Y-%m-%d"),
        "time": local.strftime("%H:%M"),
        "price": float(s.price),
        "format": s.format,
        "is_demo": s.is_demo,
        "cancelled": s.cancelled,
    }


def booking_dict(db, b):
    claims = db.scalars(select(SeatClaim).where(SeatClaim.booking_id == b.id)).all()
    tickets = db.scalars(select(Ticket).where(Ticket.booking_id == b.id)).all()
    by_claim = {t.claim_id: t for t in tickets}
    items = []
    for claim in claims:
        seat = db.get(Seat, claim.seat_id)
        t = by_claim.get(claim.id)
        items.append(
            {
                "seat_id": seat.id,
                "row": seat.row,
                "number": seat.number,
                "category": seat.category,
                "price": float(claim.price),
                "ticket_id": t.id if t else None,
                "ticket_code": t.ticket_code if t else None,
                "used_at": iso(t.used_at) if t else None,
            }
        )
    events = db.scalars(
        select(BookingEvent)
        .where(BookingEvent.booking_id == b.id)
        .order_by(BookingEvent.id)
    ).all()
    return {
        "id": b.id,
        "status": b.status,
        "total": float(b.total),
        "discount": float(b.discount),
        "currency": b.currency,
        "is_demo": b.is_demo,
        "created_at": iso(b.created_at),
        "showtime": showtime_dict(db, db.get(Showtime, b.showtime_id)),
        "items": items,
        "events": [
            {"status": e.status, "created_at": iso(e.created_at)} for e in events
        ],
    }
