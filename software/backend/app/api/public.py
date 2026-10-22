from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_, cast, String
from sqlalchemy.orm import Session
from ..db import get_db, utcnow
from ..models import Movie, Cinema, Auditorium, Showtime, Promotion
from ..services.serializers import movie_dict, cinema_dict, showtime_dict, iso
from ..services.reservations import seats_dict

router = APIRouter(prefix="/api/v1")


@router.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(select(1))
    return {"status": "ok", "payment_mode": "simulation"}


@router.get("/movies")
def movies(
    q: str = "",
    genre: str = "",
    year: int | None = None,
    min_rating: float = 0,
    max_duration: int = 600,
    age: str = "",
    status: str = "",
    language: str = "",
    sort: str = "popular",
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=50),
    db: Session = Depends(get_db),
):
    stmt = select(Movie).where(Movie.in_catalog.is_(True))
    if q:
        like = "%" + q.strip().lower() + "%"
        # SQLite lower() is ASCII-only; Python casefold below preserves Bulgarian search.
        candidates = db.scalars(stmt).all()
        ids = [
            m.id
            for m in candidates
            if q.casefold()
            in " ".join([m.title, m.original_title, *m.genres, *m.cast]).casefold()
        ]
        stmt = stmt.where(Movie.id.in_(ids))
    if genre:
        genre_ids = [m.id for m in db.scalars(select(Movie)).all() if genre in m.genres]
        stmt = stmt.where(Movie.id.in_(genre_ids))
    if year:
        stmt = stmt.where(Movie.year == year)
    if age:
        stmt = stmt.where(Movie.age == age)
    if status:
        stmt = stmt.where(Movie.status == status)
    if language:
        stmt = stmt.where(Movie.language == language)
    stmt = stmt.where(Movie.rating >= min_rating, Movie.duration <= max_duration)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    order = {
        "rating": Movie.rating.desc(),
        "newest": Movie.year.desc(),
        "title": Movie.title.asc(),
        "popular": Movie.featured.desc(),
    }.get(sort, Movie.featured.desc())
    items = db.scalars(
        stmt.order_by(order, Movie.id).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return {
        "items": [movie_dict(m) for m in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/movies/featured")
def featured(db: Session = Depends(get_db)):
    return [
        movie_dict(m)
        for m in db.scalars(
            select(Movie).where(Movie.featured.is_(True), Movie.in_catalog.is_(True))
        ).all()
    ]


@router.get("/movies/top")
def top(db: Session = Depends(get_db)):
    return [
        movie_dict(m)
        for m in db.scalars(
            select(Movie)
            .where(Movie.in_catalog.is_(True))
            .order_by(Movie.rating.desc())
            .limit(10)
        ).all()
    ]


@router.get("/movies/upcoming")
def upcoming(db: Session = Depends(get_db)):
    return [
        movie_dict(m)
        for m in db.scalars(
            select(Movie).where(Movie.status == "upcoming", Movie.in_catalog.is_(True))
        ).all()
    ]


@router.get("/movies/slug/{slug}")
def movie_slug(slug: str, db: Session = Depends(get_db)):
    m = db.scalar(select(Movie).where(Movie.slug == slug))
    if not m:
        raise HTTPException(404, "Филмът не е намерен.")
    return movie_dict(m)


@router.get("/movies/{movie_id}")
def movie(movie_id: int, db: Session = Depends(get_db)):
    m = db.get(Movie, movie_id)
    if not m:
        raise HTTPException(404, "Филмът не е намерен.")
    return movie_dict(m)


@router.get("/cinemas")
def cinemas(db: Session = Depends(get_db)):
    return [cinema_dict(c) for c in db.scalars(select(Cinema)).all()]


@router.get("/cinemas/{slug}")
def cinema(slug: str, db: Session = Depends(get_db)):
    c = db.scalar(select(Cinema).where(Cinema.slug == slug))
    if not c:
        raise HTTPException(404, "Киното не е намерено.")
    return cinema_dict(c)


@router.get("/cinemas/{cinema_id}/auditoriums")
def rooms(cinema_id: int, db: Session = Depends(get_db)):
    return [
        {"id": a.id, "name": a.name, "formats": a.formats}
        for a in db.scalars(
            select(Auditorium).where(Auditorium.cinema_id == cinema_id)
        ).all()
    ]


@router.get("/showtimes")
def showtimes(
    movie_id: int | None = None,
    cinema_id: int | None = None,
    date: str = "",
    from_hour: int = 0,
    to_hour: int = 24,
    db: Session = Depends(get_db),
):
    stmt = (
        select(Showtime)
        .join(Auditorium)
        .join(Movie, Movie.id == Showtime.movie_id)
        .where(
            Showtime.cancelled.is_(False),
            Showtime.starts_at > utcnow(),
            Movie.in_catalog.is_(True),
        )
    )
    if movie_id:
        stmt = stmt.where(Showtime.movie_id == movie_id)
    if cinema_id:
        stmt = stmt.where(Auditorium.cinema_id == cinema_id)
    if date:
        try:
            start = datetime.strptime(date, "%Y-%m-%d").replace(
                tzinfo=ZoneInfo("Europe/Sofia")
            )
        except ValueError:
            raise HTTPException(422, "Невалидна дата.")
        from datetime import timedelta

        stmt = stmt.where(
            Showtime.starts_at >= start.astimezone(timezone.utc),
            Showtime.starts_at < (start + timedelta(days=1)).astimezone(timezone.utc),
        )
    result = [
        showtime_dict(db, s)
        for s in db.scalars(stmt.order_by(Showtime.starts_at).limit(1000)).all()
    ]
    return [s for s in result if from_hour <= int(s["time"][:2]) < to_hour]


@router.get("/showtimes/{showtime_id}")
def showtime(showtime_id: int, db: Session = Depends(get_db)):
    s = db.get(Showtime, showtime_id)
    if not s:
        raise HTTPException(404, "Прожекцията не е намерена.")
    return showtime_dict(db, s)


@router.get("/showtimes/{showtime_id}/seats")
def seats(showtime_id: int, db: Session = Depends(get_db)):
    s = db.get(Showtime, showtime_id)
    if not s:
        raise HTTPException(404, "Прожекцията не е намерена.")
    return seats_dict(db, s)


@router.get("/offers")
def offers(db: Session = Depends(get_db)):
    return [
        {
            "id": p.id,
            "code": p.code,
            "title": p.title,
            "percent": p.percent,
            "minimum": float(p.minimum),
            "ends_at": iso(p.ends_at),
            "per_user": p.per_user,
            "max_uses": p.max_uses,
            "is_demo": True,
        }
        for p in db.scalars(
            select(Promotion).where(
                Promotion.active.is_(True),
                Promotion.starts_at <= utcnow(),
                Promotion.ends_at > utcnow(),
            )
        ).all()
    ]
