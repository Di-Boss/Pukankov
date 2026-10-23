from datetime import datetime
from decimal import Decimal
import re
from pydantic import BaseModel, EmailStr, Field, field_validator


class Register(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=10, max_length=64)
    terms: bool

    @field_validator("terms")
    @classmethod
    def accepted(cls, value):
        if not value:
            raise ValueError("Приемете общите условия.")
        return value


class Login(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=64)


class ProfileUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=100)


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=10, max_length=64)


class ForgotPassword(BaseModel):
    email: EmailStr


class ResetPassword(BaseModel):
    token: str = Field(min_length=20, max_length=100)
    password: str = Field(min_length=10, max_length=64)


class HoldInput(BaseModel):
    showtime_id: int
    seat_ids: list[int] = Field(min_length=1, max_length=8)

    @field_validator("seat_ids")
    @classmethod
    def unique(cls, value):
        if len(set(value)) != len(value):
            raise ValueError("Местата трябва да са различни.")
        return value


class CheckoutInput(BaseModel):
    hold_id: str = Field(max_length=64)
    promo_code: str = Field(default="", max_length=40)
    terms: bool
    transaction_success: bool = False


class PromoInput(BaseModel):
    hold_id: str = Field(max_length=64)
    code: str = Field(max_length=40)


class MovieInput(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    slug: str = Field(
        min_length=1, max_length=200, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
    )
    original_title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=10, max_length=10000)
    year: int = Field(ge=1900, le=2100)
    duration: int = Field(ge=1, le=600)
    genres: list[str] = Field(min_length=1, max_length=10)
    director: str = Field(default="", max_length=200)
    cast: list[str] = Field(default_factory=list, max_length=30)
    age: str = Field(default="12+", pattern=r"^(0|6|12|16|18)\+$")
    language: str = Field(default="Английски", max_length=50)
    subtitles: str = Field(default="Български", max_length=50)
    poster: str = Field(default="", max_length=500)
    backdrop: str = Field(default="", max_length=500)
    trailer: str = Field(default="", max_length=30)
    rating: Decimal = Field(default=0, ge=0, le=10)
    release_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    status: str = Field(default="active", pattern=r"^(active|upcoming|archived)$")
    featured: bool = False

    @field_validator("poster", "backdrop")
    @classmethod
    def safe_image(cls, value):
        if value and not value.startswith(("https://", "/images/")):
            raise ValueError("Използвайте HTTPS изображение.")
        return value

    @field_validator("trailer")
    @classmethod
    def safe_trailer(cls, value):
        if value and not re.fullmatch(r"[A-Za-z0-9_-]{11}", value):
            raise ValueError("Въведете валиден YouTube video ID.")
        return value


class ShowtimeInput(BaseModel):
    movie_id: int
    auditorium_id: int
    starts_at: datetime
    price: Decimal = Field(ge=1, le=500)
    format: str = Field(default="2D", pattern=r"^(2D|3D|IMAX|4DX)$")


class CinemaInput(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    slug: str = Field(pattern=r"^[a-z0-9-]+$", max_length=100)
    city: str = Field(min_length=2, max_length=100)
    address: str = Field(min_length=5, max_length=200)
    description: str = Field(default="", max_length=3000)
    image: str = Field(default="", max_length=500)


class AuditoriumInput(BaseModel):
    cinema_id: int
    name: str = Field(min_length=1, max_length=100)
    rows: int = Field(ge=1, le=20)
    seats_per_row: int = Field(ge=4, le=30)
    formats: list[str] = Field(default_factory=lambda: ["2D"])


class SeatUpdate(BaseModel):
    category: str = Field(pattern=r"^(standard|premium|accessible)$")
    surcharge: Decimal = Field(ge=0, le=50)
    active: bool


class PromotionInput(BaseModel):
    code: str = Field(min_length=3, max_length=40, pattern=r"^[A-Z0-9]+$")
    title: str = Field(min_length=2, max_length=100)
    percent: int = Field(ge=1, le=50)
    minimum: Decimal = Field(default=0, ge=0)
    starts_at: datetime
    ends_at: datetime
    max_uses: int = Field(default=100, ge=1)
    per_user: int = Field(default=2, ge=1)
    active: bool = True


class UserRole(BaseModel):
    role: str = Field(pattern=r"^(user|staff|admin)$")
    active: bool = True


class TicketScan(BaseModel):
    ticket_code: str = Field(pattern=r"^[0-9]{6}$")
    showtime_id: int = Field(gt=0)
