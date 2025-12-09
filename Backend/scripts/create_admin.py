import sys
from datetime import datetime
import pathlib

from bson import ObjectId  # noqa: F401 (kept for parity with project imports)

# Ensure project root is on sys.path so we can import app, db, auth when executed from scripts/
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

# Reuse the existing Flask app configuration and DB helper
from app import app
from db import get_db
from auth import hash_password


ADMIN_EMAIL = "naresh.adhikari@gmail.com"
ADMIN_PASSWORD = "Nepal123"


def ensure_admin_user() -> None:
    with app.app_context():
        db = get_db()
        users = db.users

        existing = users.find_one({"email": ADMIN_EMAIL})
        if existing:
            print(f"Admin user already exists with id: {existing.get('_id')}")
            return

        hashed_pwd = hash_password(ADMIN_PASSWORD)
        new_user = {
            "email": ADMIN_EMAIL,
            "password": hashed_pwd,
            "role": "admin",
            "created_at": datetime.utcnow(),
        }
        result = users.insert_one(new_user)
        print(f"Admin user created with id: {result.inserted_id}")


if __name__ == "__main__":
    try:
        ensure_admin_user()
    except Exception as e:
        print(f"Failed to create admin user: {e}", file=sys.stderr)
        sys.exit(1)

