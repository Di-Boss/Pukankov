from datetime import datetime, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo
from sqlalchemy import select, func
from .db import SessionLocal, utcnow
from .models import Movie, Cinema, Auditorium, Seat, Showtime, Promotion, Booking
from .original_catalog import movie_records, LEGACY_SLUGS


def seed(db):
    # Keep existing orders/accounts, but remove the previous sample films from discovery.
    legacy = db.scalars(select(Movie).where(Movie.slug.in_(LEGACY_SLUGS))).all()
    for movie in legacy:
        movie.in_catalog = False
        movie.featured = False
        movie.status = "archived"
        for show in db.scalars(
            select(Showtime).where(
                Showtime.movie_id == movie.id, Showtime.starts_at > utcnow()
            )
        ).all():
            if not db.scalar(
                select(Booking.id)
                .where(Booking.showtime_id == show.id, Booking.status == "confirmed")
                .limit(1)
            ):
                show.cancelled = True
    for record in movie_records():
        if not db.scalar(select(Movie.id).where(Movie.slug == record["slug"])):
            db.add(Movie(**record))
    db.flush()
    for cinema in db.scalars(select(Cinema)).all():
        cinema.image = "/images/originals/cinema.svg"
    if not db.scalar(select(func.count()).select_from(Cinema)):
        for name, slug, city, address in [
            ("Пуканков Витоша", "vitosha", "София", "бул. „Кино мечти“ 12"),
            ("Пуканков Капана", "kapana", "Пловдив", "ул. „Голям екран“ 8"),
            ("Пуканков Море", "more", "Варна", "бул. „Морски истории“ 24"),
        ]:
            c = Cinema(
                name=name,
                slug=slug,
                city=city,
                address=address,
                description="Място за големи истории. Лазерна прожекция, пространствен звук и удобни премиум кресла. Демонстрационно кино и адрес.",
                image="/images/originals/cinema.svg",
            )
            db.add(c)
            db.flush()
            for k in range(2):
                a = Auditorium(
                    cinema_id=c.id,
                    name=f"Зала {k+1}" + (" · IMAX" if not k else " · Dolby Atmos"),
                )
                db.add(a)
                db.flush()
                for r in range(7):
                    for n in range(1, 13):
                        premium = r in (4, 5)
                        db.add(
                            Seat(
                                auditorium_id=a.id,
                                row=chr(65 + r),
                                number=n,
                                category=(
                                    "premium"
                                    if premium
                                    else (
                                        "accessible"
                                        if r == 0 and n in (1, 12)
                                        else "standard"
                                    )
                                ),
                                surcharge=Decimal("3.00") if premium else 0,
                                accessible=r == 0 and n in (1, 12),
                            )
                        )
        db.flush()
    # Only future, explicitly demo screenings; rerun seed to roll the schedule forward.
    now = utcnow()
    rooms = db.scalars(select(Auditorium)).all()
    movies = db.scalars(
        select(Movie).where(Movie.status == "active", Movie.in_catalog.is_(True))
    ).all()
    today = datetime.now(ZoneInfo("Europe/Sofia")).date()
    for day in range(7):
        for ri, room in enumerate(rooms):
            for slot, hour in enumerate((12, 16, 20)):
                start = (
                    datetime.combine(today + timedelta(days=day), datetime.min.time())
                    .replace(hour=hour, tzinfo=ZoneInfo("Europe/Sofia"))
                    .astimezone(timezone.utc)
                )
                if start <= now or db.scalar(
                    select(Showtime.id).where(
                        Showtime.auditorium_id == room.id,
                        Showtime.starts_at == start,
                        Showtime.cancelled.is_(False),
                    )
                ):
                    continue
                m = movies[(ri * 3 + slot + day) % len(movies)]
                db.add(
                    Showtime(
                        movie_id=m.id,
                        auditorium_id=room.id,
                        starts_at=start,
                        ends_at=start + timedelta(minutes=m.duration + 20),
                        price=Decimal("12.00") if ri % 2 == 0 else Decimal("9.50"),
                        format="IMAX" if ri % 2 == 0 else "2D",
                    )
                )
    if not db.scalar(select(func.count()).select_from(Promotion)):
        db.add_all(
            [
                Promotion(
                    code="KINO20",
                    title="Киното е по-хубаво за двама",
                    percent=20,
                    minimum=18,
                    starts_at=now - timedelta(days=1),
                    ends_at=now + timedelta(days=90),
                ),
                Promotion(
                    code="STUDENT15",
                    title="Студентска кино вечер",
                    percent=15,
                    minimum=9,
                    starts_at=now - timedelta(days=1),
                    ends_at=now + timedelta(days=90),
                ),
            ]
        )
    db.commit()


if __name__ == "__main__":
    with SessionLocal() as db:
        seed(db)
    print("Demo data created. No administrator or default passwords were created.")
