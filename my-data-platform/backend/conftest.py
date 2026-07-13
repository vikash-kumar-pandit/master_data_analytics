from __future__ import annotations
import os
import sys
import uuid
from pathlib import Path

# Generate a completely unique database filename for this test session to prevent locks and collisions
TEST_DB_PATH = str(Path(__file__).parent / f"test_session_{uuid.uuid4().hex}.sqlite3")
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
os.environ["AUTH_DB_PATH"] = TEST_DB_PATH

import pytest
from datetime import datetime, timezone

# Ensure backend directory is on path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import db
import auth as auth_module

# Admin credentials matching .env / user requirements
ADMIN_USERNAME = os.getenv("TEST_ADMIN_USERNAME", "Vikash_24a12res1159@iitp.ac.in")
ADMIN_PASSWORD = os.getenv("TEST_ADMIN_PASSWORD", "Vikashkumarpandit1159@gmail.com")
ADMIN_EMAIL = os.getenv("TEST_ADMIN_EMAIL", ADMIN_USERNAME)

@pytest.fixture(scope="session", autouse=True)
def setup_unified_test_db():
    # Initialize fresh test DB
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except OSError:
            pass
    db.init_db(TEST_DB_PATH)

    # Users to seed for both test_auth.py and test_auth_rbac.py
    users = [
        {
            "username": ADMIN_USERNAME,
            "password": ADMIN_PASSWORD,
            "role":     "admin",
            "email":    ADMIN_EMAIL,
            "verified": True,
        },
        {
            "username": "admin_user",
            "password": "password123",
            "role":     "admin",
            "email":    "admin@datasaas.local",
            "verified": True,
        },
        {
            "username": "data_analyst",
            "password": "password123",
            "role":     "analyst",
            "email":    "analyst@datasaas.local",
            "verified": True,
        },
        {
            "username": "guest_viewer",
            "password": "password123",
            "role":     "viewer",
            "email":    "viewer@datasaas.local",
            "verified": True,
        },
    ]

    for user in users:
        try:
            if not db.get_user(TEST_DB_PATH, user["username"]):
                db.create_user(
                    TEST_DB_PATH,
                    user["username"],
                    auth_module.pwd_context.hash(user["password"]),
                    user["role"],
                    user["email"],
                    user["verified"],
                    datetime.now(timezone.utc),
                )
        except Exception as exc:
            pytest.skip(f"Failed to seed user {user['username']!r}: {exc}")

    yield

    # Cleanup at the end of the session
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except OSError:
            pass
