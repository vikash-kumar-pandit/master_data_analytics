"""
conftest.py — Test fixtures for backend RBAC and auth tests.

Seeds all required test users (including admin with real credentials)
into a fresh test DB before each test session.
"""
from __future__ import annotations

import os
import sys
import pytest
from pathlib import Path
from datetime import datetime, timezone

# Ensure backend directory is on path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import db
import auth as auth_module

TEST_DB_PATH = str(Path(__file__).parent / "test_auth_rbac.sqlite3")

# Admin credentials matching .env / user requirements
ADMIN_USERNAME = "Vikash_24a12res1159@iitp.ac.in"
ADMIN_PASSWORD = "Vikashkumarpandit1159@gmail.com"
ADMIN_EMAIL    = "Vikash_24a12res1159@iitp.ac.in"


@pytest.fixture(scope="session", autouse=True)
def setup_rbac_test_db():
    """Seed test database with all required roles (admin, analyst, viewer)."""
    # Point auth module at the test DB
    auth_module.DB_PATH  = TEST_DB_PATH
    auth_module.DB_path  = TEST_DB_PATH  # alias used in older code paths
    os.environ["AUTH_DB_PATH"] = TEST_DB_PATH

    # Fresh DB
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except OSError:
            pass
    db.init_db(TEST_DB_PATH)

    # Users to seed
    users = [
        {
            "username": ADMIN_USERNAME,
            "password": ADMIN_PASSWORD,
            "role":     "admin",
            "email":    ADMIN_EMAIL,
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

    # Cleanup
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except OSError:
            pass
