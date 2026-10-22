from datetime import datetime
from decimal import Decimal
from sqlalchemy import (
    String,
    Text,
    ForeignKey,
    Numeric,
    DateTime,
    UniqueConstraint,
    Index,
    CheckConstraint,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base, utcnow, UTCDateTime


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="user")
    active: Mapped[bool] = mapped_column(default=True)
    deletion_requested: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class Session(Base):
    __tablename__ = "sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)


class PasswordReset(Base):
    __tablename__ = "password_reset_tokens"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)
    used: Mapped[bool] = mapped_column(default=False)


class Movie(Base):
    __tablename__ = "movies"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    slug: Mapped[str] = mapped_column(String(200), unique=True)
    original_title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    year: Mapped[int]
    duration: Mapped[int]
    genres: Mapped[list] = mapped_column(JSON)
    director: Mapped[str] = mapped_column(String(200))
    cast: Mapped[list] = mapped_column(JSON)
    age: Mapped[str] = mapped_column(String(10), default="12+")
    language: Mapped[str] = mapped_column(String(50), default="Английски")
    subtitles: Mapped[str] = mapped_column(String(50), default="Български")
    poster: Mapped[str] = mapped_column(String(500))
    backdrop: Mapped[str] = mapped_column(String(500))
    trailer: Mapped[str] = mapped_column(String(30), default="")
    rating: Mapped[Decimal] = mapped_column(Numeric(3, 1))
    rating_count: Mapped[int] = mapped_column(default=0)
    release_date: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    featured: Mapped[bool] = mapped_column(default=False)
    in_catalog: Mapped[bool] = mapped_column(
        default=True, server_default="1", index=True
    )
    is_demo: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utcnow, onupdate=utcnow
    )
    __table_args__ = (
        CheckConstraint("duration > 0"),
        CheckConstraint("rating >= 0 AND rating <= 10"),
    )


class Cinema(Base):
    __tablename__ = "cinemas"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    city: Mapped[str] = mapped_column(String(100))
    address: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    image: Mapped[str] = mapped_column(String(500))
    is_demo: Mapped[bool] = mapped_column(default=True)


class Auditorium(Base):
    __tablename__ = "auditoriums"
    id: Mapped[int] = mapped_column(primary_key=True)
    cinema_id: Mapped[int] = mapped_column(ForeignKey("cinemas.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    formats: Mapped[list] = mapped_column(JSON, default=lambda: ["2D", "IMAX"])


class Seat(Base):
    __tablename__ = "seats"
    id: Mapped[int] = mapped_column(primary_key=True)
    auditorium_id: Mapped[int] = mapped_column(ForeignKey("auditoriums.id"), index=True)
    row: Mapped[str] = mapped_column(String(5))
    number: Mapped[int]
    category: Mapped[str] = mapped_column(String(20), default="standard")
    surcharge: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    accessible: Mapped[bool] = mapped_column(default=False)
    active: Mapped[bool] = mapped_column(default=True)
    __table_args__ = (UniqueConstraint("auditorium_id", "row", "number"),)


class Showtime(Base):
    __tablename__ = "showtimes"
    id: Mapped[int] = mapped_column(primary_key=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"), index=True)
    auditorium_id: Mapped[int] = mapped_column(ForeignKey("auditoriums.id"), index=True)
    starts_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    ends_at: Mapped[datetime] = mapped_column(UTCDateTime)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    format: Mapped[str] = mapped_column(String(20), default="2D")
    cancelled: Mapped[bool] = mapped_column(default=False)
    is_demo: Mapped[bool] = mapped_column(default=True)
    __table_args__ = (
        CheckConstraint("price >= 0"),
        Index("ix_showtime_room_time", "auditorium_id", "starts_at"),
    )


class Hold(Base):
    __tablename__ = "holds"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    showtime_id: Mapped[int] = mapped_column(ForeignKey("showtimes.id"))
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    status: Mapped[str] = mapped_column(String(20), default="active")


class Booking(Base):
    __tablename__ = "bookings"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    hold_id: Mapped[str] = mapped_column(ForeignKey("holds.id"), unique=True)
    showtime_id: Mapped[int] = mapped_column(ForeignKey("showtimes.id"))
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    discount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    status: Mapped[str] = mapped_column(String(30), default="pending")
    is_demo: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class SeatClaim(Base):
    __tablename__ = "showtime_seat_claims"
    id: Mapped[int] = mapped_column(primary_key=True)
    showtime_id: Mapped[int] = mapped_column(ForeignKey("showtimes.id"))
    seat_id: Mapped[int] = mapped_column(ForeignKey("seats.id"))
    hold_id: Mapped[str] = mapped_column(ForeignKey("holds.id"), index=True)
    booking_id: Mapped[str | None] = mapped_column(
        ForeignKey("bookings.id"), nullable=True
    )
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    __table_args__ = (
        UniqueConstraint("showtime_id", "seat_id", name="uq_showtime_seat_claim"),
    )


class Ticket(Base):
    __tablename__ = "tickets"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    booking_id: Mapped[str] = mapped_column(ForeignKey("bookings.id"), index=True)
    claim_id: Mapped[int] = mapped_column(
        ForeignKey("showtime_seat_claims.id"), unique=True
    )
    ticket_code: Mapped[str] = mapped_column(String(6), unique=True)
    used_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)


class Payment(Base):
    __tablename__ = "payments"
    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[str] = mapped_column(ForeignKey("bookings.id"), unique=True)
    provider: Mapped[str] = mapped_column(String(20), default="demo")
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    status: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class BookingEvent(Base):
    __tablename__ = "booking_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[str] = mapped_column(ForeignKey("bookings.id"), index=True)
    status: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class Promotion(Base):
    __tablename__ = "promotions"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True)
    title: Mapped[str] = mapped_column(String(100))
    percent: Mapped[int]
    minimum: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    starts_at: Mapped[datetime] = mapped_column(UTCDateTime)
    ends_at: Mapped[datetime] = mapped_column(UTCDateTime)
    max_uses: Mapped[int] = mapped_column(default=100)
    per_user: Mapped[int] = mapped_column(default=2)
    active: Mapped[bool] = mapped_column(default=True)
    __table_args__ = (CheckConstraint("percent > 0 AND percent <= 50"),)


class Redemption(Base):
    __tablename__ = "promotion_redemptions"
    id: Mapped[int] = mapped_column(primary_key=True)
    promotion_id: Mapped[int] = mapped_column(ForeignKey("promotions.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    booking_id: Mapped[str] = mapped_column(ForeignKey("bookings.id"), unique=True)


class Favorite(Base):
    __tablename__ = "favorites"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"), primary_key=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(100))
    object_id: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class Device(Base):
    __tablename__ = "devices"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(20))
    key_hash: Mapped[str] = mapped_column(String(64), unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    auditorium_id: Mapped[int | None] = mapped_column(
        ForeignKey("auditoriums.id"), nullable=True
    )
    active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
