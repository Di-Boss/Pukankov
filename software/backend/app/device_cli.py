"""Provision per-device credentials; no shared or hardcoded hardware API keys."""

import argparse
import secrets
from sqlalchemy import select
from .db import SessionLocal
from .models import Device, User, Auditorium
from .core.security import digest, hash_password


def main():
    parser = argparse.ArgumentParser(
        description="Provision/revoke a cinema terminal or entry validator."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create")
    create.add_argument("--name", required=True)
    create.add_argument("--role", choices=["kiosk", "validator"], required=True)
    create.add_argument("--auditorium-id", type=int)
    revoke = commands.add_parser("revoke")
    revoke.add_argument("device_id")
    args = parser.parse_args()
    with SessionLocal() as db:
        if args.command == "revoke":
            device = db.get(Device, args.device_id)
            if not device:
                raise SystemExit("Device not found.")
            device.active = False
            db.commit()
            print("Device revoked.")
            return
        if args.auditorium_id is not None and not db.get(
            Auditorium, args.auditorium_id
        ):
            raise SystemExit("Auditorium not found.")
        device_id = secrets.token_hex(12)
        token = "pk_device_" + secrets.token_urlsafe(32)
        user = User(
            name=args.name,
            email=f"device-{device_id}@pukankov.invalid",
            role="user",
            active=False,
            password_hash=hash_password(secrets.token_urlsafe(40)),
        )
        db.add(user)
        db.flush()
        db.add(
            Device(
                id=device_id,
                name=args.name,
                role=args.role,
                key_hash=digest(token),
                user_id=user.id,
                auditorium_id=args.auditorium_id,
            )
        )
        db.commit()
    print(
        f"Device ID: {device_id}\nAuthorization: Bearer {token}\nKeep this credential locally. It will not be displayed again."
    )


if __name__ == "__main__":
    main()
