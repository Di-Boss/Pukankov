import secrets
from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from ..db import utcnow
from ..models import Ticket, Booking, Showtime, SeatClaim, Seat, Movie, AuditLog


def issue_ticket(db, booking_id, claim_id):
    """Unique DB constraint + savepoint retries also protect concurrent screenings."""
    for _ in range(128):
        ticket = Ticket(
            id=secrets.token_urlsafe(14),
            booking_id=booking_id,
            claim_id=claim_id,
            ticket_code=str(100000 + secrets.randbelow(900000)),
        )
        try:
            with db.begin_nested():
                db.add(ticket)
                db.flush()
            return ticket
        except IntegrityError:
            # Only code collisions are retried. Other invariant violations stay visible.
            if not db.scalar(
                select(Ticket.id).where(Ticket.ticket_code == ticket.ticket_code)
            ):
                raise
    raise HTTPException(503, "Не успяхме да издадем уникален код. Опитайте отново.")


def validate_ticket(db, code, showtime_id, actor_user_id, auditorium_id=None):
    t = db.scalar(select(Ticket).where(Ticket.ticket_code == code).with_for_update())
    if not t:
        return {
            "valid": False,
            "reason": "invalid_code",
            "message": "Невалиден код на билет.",
        }
    booking = db.get(Booking, t.booking_id)
    show = db.get(Showtime, booking.showtime_id)
    if (showtime_id is not None and show.id != showtime_id) or (
        auditorium_id is not None and show.auditorium_id != auditorium_id
    ):
        return {
            "valid": False,
            "reason": "wrong_showtime",
            "message": "Билетът е за друга прожекция или зала.",
        }
    if booking.status != "confirmed" or show.cancelled:
        return {
            "valid": False,
            "reason": "cancelled",
            "message": "Билетът не е потвърден или прожекцията е отменена.",
        }
    if show.ends_at <= utcnow():
        return {
            "valid": False,
            "reason": "expired",
            "message": "Прожекцията вече е приключила.",
        }
    if t.used_at:
        return {
            "valid": False,
            "reason": "already_used",
            "message": "Билетът вече е използван.",
        }
    # SQLite does not implement SELECT FOR UPDATE. The conditional update also
    # makes consumption atomic there, as well as under PostgreSQL row locks.
    consumed = db.execute(
        update(Ticket)
        .where(Ticket.id == t.id, Ticket.used_at.is_(None))
        .values(used_at=utcnow())
        .execution_options(synchronize_session=False)
    )
    if consumed.rowcount != 1:
        return {"valid": False, "reason": "already_used", "message": "Билетът вече е използван."}
    db.expire(t, ["used_at"])
    claim = db.get(SeatClaim, t.claim_id)
    seat = db.get(Seat, claim.seat_id)
    db.add(AuditLog(user_id=actor_user_id, action="ticket.validate", object_id=t.id))
    db.flush()
    return {
        "valid": True,
        "message": "Билетът е валиден. Достъпът е разрешен.",
        "ticket_code": t.ticket_code,
        "movie": db.get(Movie, show.movie_id).title,
        "seat": f"{seat.row}{seat.number}",
        "showtime_id": show.id,
        "status": "used",
    }
