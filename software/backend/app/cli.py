import argparse
from getpass import getpass
from sqlalchemy import select
from .db import SessionLocal, Base, engine
from .models import User
from .core.security import hash_password


def main():
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=["create-admin"])
    p.add_argument("--email", required=True)
    p.add_argument("--name", default="Администратор")
    args = p.parse_args()
    password = getpass("New password (10–64 characters): ")
    if not 10 <= len(password) <= 64:
        raise SystemExit("Password must contain 10–64 characters.")
    if password != getpass("Confirm password: "):
        raise SystemExit("Passwords differ.")
    from pydantic import TypeAdapter, EmailStr

    email = str(TypeAdapter(EmailStr).validate_python(args.email)).lower()
    with SessionLocal() as db:
        if db.scalar(select(User.id).where(User.email == email)):
            raise SystemExit("User already exists. No changes made.")
        db.add(
            User(
                email=email,
                name=args.name,
                role="admin",
                password_hash=hash_password(password),
            )
        )
        db.commit()
    print("Administrator created. Sign in through /login.")


if __name__ == "__main__":
    main()
