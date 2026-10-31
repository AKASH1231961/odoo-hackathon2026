"""
Runs once before the API and workers start (the `migrate` service in Docker).
Brings the schema up to date, adds demo data if asked, and makes sure an admin exists.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.core.config import settings
from app.core.database import SessionLocal, engine
from app.core.security import hash_password, validate_password_policy
from app.models.user import User, UserRole

BASELINE = "0001"


def migrate():
    config = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    tables = set(inspect(engine).get_table_names())
    # Databases created before migrations existed already hold the baseline tables
    if "users" in tables and "alembic_version" not in tables:
        print("[prestart] Existing tables found, marking them as the baseline")
        command.stamp(config, BASELINE)
    command.upgrade(config, "head")


def ensure_admin():
    db = SessionLocal()
    try:
        if db.query(User).filter(User.role == UserRole.admin).first():
            return
        email = settings.ADMIN_EMAIL.strip().lower()
        if not email or not settings.ADMIN_PASSWORD:
            print("[prestart] No admin exists. Set ADMIN_EMAIL and ADMIN_PASSWORD to create one.")
            return
        if not validate_password_policy(settings.ADMIN_PASSWORD):
            sys.exit("[prestart] ADMIN_PASSWORD does not meet the password policy")
        db.add(
            User(
                email=email,
                full_name="Administrator",
                password_hash=hash_password(settings.ADMIN_PASSWORD),
                role=UserRole.admin,
            )
        )
        db.commit()
        print(f"[prestart] Created admin {email}")
    finally:
        db.close()


if __name__ == "__main__":
    migrate()
    if settings.SEED_DEMO_DATA:
        import seed

        seed.run()
    ensure_admin()
