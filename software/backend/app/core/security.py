import hashlib
import secrets
from collections import defaultdict, deque
from datetime import timedelta
from time import monotonic
import bcrypt
from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session as DBSession
from ..db import get_db, utcnow
from ..models import Session, User
from .config import settings


def digest(value: str):
    return hashlib.sha256(value.encode()).hexdigest()


def hash_password(password):
    # Prehash supports Unicode passwords without bcrypt's 72-byte truncation.
    return bcrypt.hashpw(digest(password).encode(), bcrypt.gensalt()).decode()


def verify_password(password, hashed):
    return bcrypt.checkpw(digest(password).encode(), hashed.encode())


DUMMY_PASSWORD_HASH = hash_password(secrets.token_urlsafe(32))


def create_session(db, user, response):
    token = secrets.token_urlsafe(48)
    db.add(
        Session(
            token_hash=digest(token),
            user_id=user.id,
            expires_at=utcnow() + timedelta(hours=12),
        )
    )
    response.set_cookie(
        "pukankov_session",
        token,
        httponly=True,
        secure=settings.environment == "production",
        samesite="lax",
        max_age=43200,
        path="/",
    )


def current_user(request: Request, db: DBSession = Depends(get_db)):
    token = request.cookies.get("pukankov_session", "")
    session = db.get(Session, digest(token)) if token else None
    user = (
        db.get(User, session.user_id)
        if session and session.expires_at > utcnow()
        else None
    )
    if not user or not user.active:
        raise HTTPException(401, "Влезте в профила си, за да продължите.")
    return user


def admin_user(user: User = Depends(current_user)):
    if user.role != "admin":
        raise HTTPException(403, "Нямате административни права.")
    return user


def staff_user(user: User = Depends(current_user)):
    if user.role not in ("staff", "admin"):
        raise HTTPException(403, "Нямате права за проверка на билети.")
    return user


class RateLimiter:
    def __init__(self):
        self.attempts = defaultdict(deque)

    def check(self, key, limit=10, window=300):
        now = monotonic()
        q = self.attempts[key]
        while q and q[0] <= now - window:
            q.popleft()
        if len(q) >= limit:
            raise HTTPException(
                429, "Твърде много опити. Опитайте отново след няколко минути."
            )
        q.append(now)


limiter = RateLimiter()


def public_user(user):
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "deletion_requested": user.deletion_requested,
    }
