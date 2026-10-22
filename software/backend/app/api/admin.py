from datetime import timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from ..db import get_db, utcnow
from ..models import (
    User,
    Movie,
    Cinema,
    Auditorium,
    Seat,
    Showtime,
    Booking,
    Ticket,
    Promotion,
    AuditLog,
    SeatClaim,
)
from ..schemas import (
    MovieInput,
    ShowtimeInput,
    CinemaInput,
    AuditoriumInput,
    SeatUpdate,
    PromotionInput,
    UserRole,
)
from ..core.security import admin_user, public_user
from ..services.serializers import (
    movie_dict,
    cinema_dict,
    showtime_dict,
    booking_dict,
    iso,
)

router = APIRouter(prefix="/api/v1/admin", dependencies=[Depends(admin_user)])


def audit(db, u, action, obj):
    db.add(AuditLog(user_id=u.id, action=action, object_id=str(obj)))


def to_utc(dt):
    if dt.tzinfo is None:
        raise HTTPException(422, "Посочете час с часова зона.")
    return dt.astimezone(timezone.utc)


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    confirmed = Booking.status == "confirmed"
    revenue = db.scalar(
        select(func.coalesce(func.sum(Booking.total), 0)).where(confirmed)
    )
    orders = db.scalar(select(func.count()).select_from(Booking).where(confirmed))
    sold = db.scalar(select(func.count()).select_from(Ticket))
    shows = db.scalar(
        select(func.count())
        .select_from(Showtime)
        .where(Showtime.starts_at > utcnow(), Showtime.cancelled.is_(False))
    )
    by_movie = db.execute(
        select(Movie.title, func.count(Ticket.id))
        .select_from(Ticket)
        .join(Booking, Booking.id == Ticket.booking_id)
        .join(Showtime, Showtime.id == Booking.showtime_id)
        .join(Movie, Movie.id == Showtime.movie_id)
        .group_by(Movie.title)
    ).all()
    by_day = db.execute(
        select(func.date(Booking.created_at), func.sum(Booking.total))
        .where(confirmed)
        .group_by(func.date(Booking.created_at))
        .order_by(func.date(Booking.created_at))
    ).all()
    return {
        "revenue": float(revenue),
        "orders": orders,
        "tickets": sold,
        "showtimes": shows,
        "movies": db.scalar(
            select(func.count()).select_from(Movie).where(Movie.in_catalog.is_(True))
        ),
        "users": db.scalar(select(func.count()).select_from(User)),
        "average": float(revenue / orders) if orders else 0,
        "by_movie": [{"title": t, "tickets": n} for t, n in by_movie],
        "by_day": [{"date": str(d), "total": float(v)} for d, v in by_day],
        "is_demo": True,
    }


@router.get("/movies")
def movies(db: Session = Depends(get_db)):
    return [
        movie_dict(m)
        for m in db.scalars(
            select(Movie).where(Movie.in_catalog.is_(True)).order_by(Movie.id.desc())
        ).all()
    ]


@router.post("/movies", status_code=201)
def add_movie(
    data: MovieInput, u: User = Depends(admin_user), db: Session = Depends(get_db)
):
    if db.scalar(select(Movie.id).where(Movie.slug == data.slug)):
        raise HTTPException(409, "Този slug вече съществува.")
    m = Movie(**data.model_dump())
    db.add(m)
    db.flush()
    audit(db, u, "movie.create", m.id)
    return movie_dict(m)


@router.put("/movies/{movie_id}")
def edit_movie(
    movie_id: int,
    data: MovieInput,
    u: User = Depends(admin_user),
    db: Session = Depends(get_db),
):
    m = db.get(Movie, movie_id)
    if not m:
        raise HTTPException(404, "Филмът не е намерен.")
    if db.scalar(select(Movie.id).where(Movie.slug == data.slug, Movie.id != movie_id)):
        raise HTTPException(409, "Този slug вече съществува.")
    if data.duration != m.duration and db.scalar(
        select(Showtime.id)
        .where(
            Showtime.movie_id == m.id,
            Showtime.starts_at > utcnow(),
            Showtime.cancelled.is_(False),
        )
        .limit(1)
    ):
        raise HTTPException(
            409, "Отменете бъдещите прожекции, преди да промените продължителността."
        )
    for k, v in data.model_dump().items():
        setattr(m, k, v)
    audit(db, u, "movie.update", m.id)
    db.flush()
    return movie_dict(m)


@router.delete("/movies/{movie_id}")
def archive_movie(
    movie_id: int, u: User = Depends(admin_user), db: Session = Depends(get_db)
):
    m = db.get(Movie, movie_id)
    if not m:
        raise HTTPException(404, "Филмът не е намерен.")
    m.status = "archived"
    audit(db, u, "movie.archive", m.id)
    return {"message": "Филмът е архивиран."}


@router.get("/showtimes")
def showtimes(db: Session = Depends(get_db)):
    return [
        showtime_dict(db, s)
        for s in db.scalars(
            select(Showtime)
            .where(Showtime.starts_at > utcnow())
            .order_by(Showtime.starts_at)
        ).all()
    ]


@router.post("/showtimes", status_code=201)
def add_showtime(
    data: ShowtimeInput, u: User = Depends(admin_user), db: Session = Depends(get_db)
):
    room = db.scalar(
        select(Auditorium).where(Auditorium.id == data.auditorium_id).with_for_update()
    )
    m = db.get(Movie, data.movie_id)
    if not room or not m:
        raise HTTPException(404, "Невалиден филм или зала.")
    if data.format not in room.formats:
        raise HTTPException(422, "Форматът не се поддържа от залата.")
    start = to_utc(data.starts_at)
    end = start + timedelta(minutes=m.duration + 20)
    if start <= utcnow():
        raise HTTPException(422, "Прожекцията трябва да бъде в бъдещето.")
    conflict = db.scalar(
        select(Showtime.id)
        .where(
            Showtime.auditorium_id == room.id,
            Showtime.cancelled.is_(False),
            Showtime.starts_at < end,
            Showtime.ends_at > start,
        )
        .limit(1)
    )
    if conflict:
        raise HTTPException(
            409, "Прожекциите се застъпват. Включени са 20 минути за подготовка."
        )
    s = Showtime(
        movie_id=m.id,
        auditorium_id=room.id,
        starts_at=start,
        ends_at=end,
        price=data.price,
        format=data.format,
    )
    db.add(s)
    db.flush()
    audit(db, u, "showtime.create", s.id)
    return showtime_dict(db, s)


@router.delete("/showtimes/{showtime_id}")
def cancel_showtime(
    showtime_id: int, u: User = Depends(admin_user), db: Session = Depends(get_db)
):
    s = db.scalar(select(Showtime).where(Showtime.id == showtime_id).with_for_update())
    if not s:
        raise HTTPException(404, "Прожекцията не е намерена.")
    if db.scalar(
        select(Booking.id)
        .where(Booking.showtime_id == s.id, Booking.status == "confirmed")
        .limit(1)
    ):
        raise HTTPException(
            409,
            "Прожекцията има продадени билети. Нужна е отделна процедура за анулиране и възстановяване.",
        )
    s.cancelled = True
    audit(db, u, "showtime.cancel", s.id)
    return {"message": "Прожекцията е отменена."}


@router.get("/cinemas")
def cinemas(db: Session = Depends(get_db)):
    return [cinema_dict(c) for c in db.scalars(select(Cinema)).all()]


@router.post("/cinemas", status_code=201)
def add_cinema(
    data: CinemaInput, u: User = Depends(admin_user), db: Session = Depends(get_db)
):
    c = Cinema(**data.model_dump())
    db.add(c)
    db.flush()
    audit(db, u, "cinema.create", c.id)
    return cinema_dict(c)


@router.get("/auditoriums")
def rooms(db: Session = Depends(get_db)):
    return [
        {
            "id": a.id,
            "name": a.name,
            "cinema_id": a.cinema_id,
            "formats": a.formats,
            "capacity": db.scalar(
                select(func.count()).select_from(Seat).where(Seat.auditorium_id == a.id)
            ),
        }
        for a in db.scalars(select(Auditorium)).all()
    ]


@router.post("/auditoriums", status_code=201)
def add_room(
    data: AuditoriumInput, u: User = Depends(admin_user), db: Session = Depends(get_db)
):
    if not db.get(Cinema, data.cinema_id):
        raise HTTPException(404, "Киното не е намерено.")
    a = Auditorium(cinema_id=data.cinema_id, name=data.name, formats=data.formats)
    db.add(a)
    db.flush()
    for r in range(data.rows):
        for n in range(1, data.seats_per_row + 1):
            db.add(Seat(auditorium_id=a.id, row=chr(65 + r), number=n))
    audit(db, u, "auditorium.create", a.id)
    return {"id": a.id, "name": a.name}


@router.patch("/seats/{seat_id}")
def update_seat(
    seat_id: int,
    data: SeatUpdate,
    u: User = Depends(admin_user),
    db: Session = Depends(get_db),
):
    s = db.get(Seat, seat_id)
    if not s:
        raise HTTPException(404, "Мястото не е намерено.")
    if db.scalar(select(SeatClaim.id).where(SeatClaim.seat_id == s.id).limit(1)):
        raise HTTPException(
            409, "Мястото има резервации. Схемата не може да бъде променена."
        )
    for k, v in data.model_dump().items():
        setattr(s, k, v)
    audit(db, u, "seat.update", s.id)
    return {"message": "Мястото е обновено."}


@router.get("/orders")
def orders(db: Session = Depends(get_db)):
    return [
        dict(booking_dict(db, b), user_email=db.get(User, b.user_id).email)
        for b in db.scalars(
            select(Booking).order_by(Booking.created_at.desc()).limit(200)
        ).all()
    ]


@router.get("/users")
def users(
    q: str = "",
    role: str = "",
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
):
    stmt = select(User)
    if q:
        stmt = stmt.where(User.email.contains(q.lower()))
    if role:
        stmt = stmt.where(User.role == role)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    return {
        "items": [
            dict(public_user(u), active=u.active, created_at=iso(u.created_at))
            for u in db.scalars(
                stmt.order_by(User.id).offset((page - 1) * 20).limit(20)
            ).all()
        ],
        "total": total,
    }


@router.patch("/users/{user_id}")
def update_user(
    user_id: int,
    data: UserRole,
    u: User = Depends(admin_user),
    db: Session = Depends(get_db),
):
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(404, "Потребителят не е намерен.")
    if target.id == u.id:
        raise HTTPException(409, "Не можете да променяте собствените си права.")
    target.role = data.role
    target.active = data.active
    audit(db, u, "user.update", target.id)
    return public_user(target)


@router.get("/promotions")
def promotions(db: Session = Depends(get_db)):
    return [
        {
            c.name: (
                iso(getattr(p, c.name))
                if c.name.endswith("_at")
                else (
                    float(getattr(p, c.name))
                    if c.name == "minimum"
                    else getattr(p, c.name)
                )
            )
            for c in Promotion.__table__.columns
        }
        for p in db.scalars(select(Promotion)).all()
    ]


@router.post("/promotions", status_code=201)
def add_promotion(
    data: PromotionInput, u: User = Depends(admin_user), db: Session = Depends(get_db)
):
    if db.scalar(select(Promotion.id).where(Promotion.code == data.code)):
        raise HTTPException(409, "Кодът вече съществува.")
    values = data.model_dump()
    values["starts_at"] = to_utc(data.starts_at)
    values["ends_at"] = to_utc(data.ends_at)
    if values["ends_at"] <= values["starts_at"]:
        raise HTTPException(422, "Краят трябва да е след началото.")
    p = Promotion(**values)
    db.add(p)
    db.flush()
    audit(db, u, "promotion.create", p.id)
    return {"id": p.id, "code": p.code}


@router.delete("/promotions/{promotion_id}")
def disable_promo(
    promotion_id: int, u: User = Depends(admin_user), db: Session = Depends(get_db)
):
    p = db.get(Promotion, promotion_id)
    if not p:
        raise HTTPException(404, "Промокодът не е намерен.")
    p.active = False
    audit(db, u, "promotion.disable", p.id)
    return {"message": "Промокодът е деактивиран."}


@router.get("/audit-logs")
def audit_logs(db: Session = Depends(get_db)):
    return [
        {
            "id": a.id,
            "user_id": a.user_id,
            "action": a.action,
            "object_id": a.object_id,
            "created_at": iso(a.created_at),
        }
        for a in db.scalars(
            select(AuditLog).order_by(AuditLog.id.desc()).limit(200)
        ).all()
    ]
