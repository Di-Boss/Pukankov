import secrets
from datetime import timedelta
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    BackgroundTasks,
)
from sqlalchemy import select, delete
from sqlalchemy.orm import Session as DBSession
from ..db import get_db, utcnow
from ..models import User, Session, PasswordReset, Favorite, Movie, Booking
from ..schemas import (
    Register,
    Login,
    ProfileUpdate,
    PasswordChange,
    ForgotPassword,
    ResetPassword,
)
from ..core.security import (
    hash_password,
    verify_password,
    create_session,
    digest,
    current_user,
    public_user,
    limiter,
    DUMMY_PASSWORD_HASH,
)
from ..core.config import settings
from ..services.serializers import movie_dict, booking_dict
from ..services.email import send_email

router = APIRouter(prefix="/api/v1")


@router.post("/auth/register", status_code=201)
def register(
    data: Register,
    request: Request,
    response: Response,
    db: DBSession = Depends(get_db),
):
    limiter.check(("register", request.client.host), limit=10)
    email = str(data.email).lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "Вече има профил с този имейл.")
    u = User(
        name=data.name.strip(), email=email, password_hash=hash_password(data.password)
    )
    db.add(u)
    db.flush()
    create_session(db, u, response)
    return public_user(u)


@router.post("/auth/login")
def login(
    data: Login, request: Request, response: Response, db: DBSession = Depends(get_db)
):
    limiter.check(("login", request.client.host), limit=20)
    limiter.check(("email", str(data.email).lower()), limit=10)
    u = db.scalar(select(User).where(User.email == str(data.email).lower()))
    valid = verify_password(
        data.password, u.password_hash if u else DUMMY_PASSWORD_HASH
    )
    if not u or not valid or not u.active:
        raise HTTPException(401, "Невалиден имейл или парола.")
    create_session(db, u, response)
    return public_user(u)


@router.post("/auth/logout")
def logout(request: Request, response: Response, db: DBSession = Depends(get_db)):
    db.execute(
        delete(Session).where(
            Session.token_hash == digest(request.cookies.get("pukankov_session", ""))
        )
    )
    response.delete_cookie("pukankov_session", path="/")
    return {"message": "Излязохте от профила си."}


@router.get("/me")
def me(u: User = Depends(current_user)):
    return public_user(u)


@router.patch("/me")
def update_me(
    data: ProfileUpdate,
    u: User = Depends(current_user),
    db: DBSession = Depends(get_db),
):
    u.name = data.name.strip()
    db.flush()
    return public_user(u)


@router.post("/me/password")
def password(
    data: PasswordChange,
    response: Response,
    u: User = Depends(current_user),
    db: DBSession = Depends(get_db),
):
    if not verify_password(data.current_password, u.password_hash):
        raise HTTPException(422, "Текущата парола е невалидна.")
    u.password_hash = hash_password(data.password)
    db.execute(delete(Session).where(Session.user_id == u.id))
    create_session(db, u, response)
    return {"message": "Паролата е обновена. Другите сесии са прекратени."}


@router.delete("/me")
def delete_me(u: User = Depends(current_user), db: DBSession = Depends(get_db)):
    u.deletion_requested = True
    return {"message": "Заявката за изтриване е записана за преглед от администратора."}


@router.get("/me/export")
def export_me(u: User = Depends(current_user), db: DBSession = Depends(get_db)):
    return {
        "profile": public_user(u),
        "bookings": [
            booking_dict(db, b)
            for b in db.scalars(select(Booking).where(Booking.user_id == u.id)).all()
        ],
    }


@router.post("/auth/forgot-password")
def forgot(
    data: ForgotPassword,
    request: Request,
    tasks: BackgroundTasks,
    db: DBSession = Depends(get_db),
):
    limiter.check(("reset", request.client.host), limit=5)
    u = db.scalar(select(User).where(User.email == str(data.email).lower()))
    if u and settings.smtp_host:
        token = secrets.token_urlsafe(32)
        db.add(
            PasswordReset(
                token_hash=digest(token),
                user_id=u.id,
                expires_at=utcnow() + timedelta(minutes=30),
            )
        )
        tasks.add_task(
            send_email,
            u.email,
            "Пуканков · Възстановяване на парола",
            f"Отворете {settings.public_origin}/forgot-password#token={token} в рамките на 30 минути. Ако не сте поискали промяна, игнорирайте съобщението.",
        )
    return {
        "message": "Ако профилът съществува и имейл услугата е настроена, ще получите инструкции.",
        "email_configured": bool(settings.smtp_host),
    }


@router.post("/auth/reset-password")
def reset(data: ResetPassword, request: Request, db: DBSession = Depends(get_db)):
    limiter.check(("reset-token", request.client.host), limit=10)
    r = db.scalar(
        select(PasswordReset)
        .where(PasswordReset.token_hash == digest(data.token))
        .with_for_update()
    )
    if not r or r.used or r.expires_at <= utcnow():
        raise HTTPException(422, "Невалиден или изтекъл линк.")
    u = db.get(User, r.user_id)
    u.password_hash = hash_password(data.password)
    r.used = True
    db.execute(delete(Session).where(Session.user_id == u.id))
    return {"message": "Паролата е променена. Можете да влезете."}


@router.get("/me/favorites")
def favorites(u: User = Depends(current_user), db: DBSession = Depends(get_db)):
    return [
        movie_dict(m)
        for m in db.scalars(
            select(Movie).join(Favorite).where(Favorite.user_id == u.id)
        ).all()
    ]


@router.post("/me/favorites/{movie_id}")
def add_favorite(
    movie_id: int, u: User = Depends(current_user), db: DBSession = Depends(get_db)
):
    if not db.get(Movie, movie_id):
        raise HTTPException(404, "Филмът не е намерен.")
    if not db.get(Favorite, (u.id, movie_id)):
        db.add(Favorite(user_id=u.id, movie_id=movie_id))
    return {"saved": True}


@router.delete("/me/favorites/{movie_id}")
def delete_favorite(
    movie_id: int, u: User = Depends(current_user), db: DBSession = Depends(get_db)
):
    db.execute(
        delete(Favorite).where(Favorite.user_id == u.id, Favorite.movie_id == movie_id)
    )
    return {"saved": False}
