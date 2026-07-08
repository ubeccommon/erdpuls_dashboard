#!/usr/bin/env python3
"""
create_admin.py — bootstrap (or promote) an admin user.

The repo's DEPLOY.md references this script but the file is missing from the repo,
so this is a faithful replacement. It reuses the app's OWN password hashing
(app.auth.hash_password → bcrypt, gensalt rounds=12, 72-byte truncation) and the
app.models.User model, so the stored hash and columns exactly match what login
expects. No hashing logic is reimplemented here.

Run from the app root with the venv so `app.*` imports resolve and `.env` loads:
    cd /srv/ubec/erdpuls
    venv/bin/python create_admin.py <email> <password> "<name>"

If the email already exists, it is promoted to an active admin with the new
password rather than duplicated.
"""
import sys

from app.database import SessionLocal
from app.models import User
from app.auth import hash_password


def main() -> int:
    if len(sys.argv) != 4:
        print('Usage: python create_admin.py <email> <password> "<name>"')
        return 2

    email, password, name = sys.argv[1], sys.argv[2], sys.argv[3]
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            user.password_hash = hash_password(password)
            user.name = name
            user.role = "admin"
            user.is_active = True
            user.email_verified = True
            action = "Promoted existing user to admin"
        else:
            user = User(
                email=email,
                password_hash=hash_password(password),
                name=name,
                role="admin",
                is_active=True,
                email_verified=True,
            )
            db.add(user)
            action = "Created admin"
        db.commit()
        print(f"{action}: {email}")
        return 0
    except Exception as exc:  # surface DB/constraint errors clearly (e.g. role check)
        db.rollback()
        print(f"FAILED: {type(exc).__name__}: {exc}")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
