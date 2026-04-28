from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timezone, timedelta
from typing import Any
import os

DB_SCHEMA = {
    "users": (
        "CREATE TABLE IF NOT EXISTS users ("
        "username TEXT PRIMARY KEY,"
        "password_hash TEXT NOT NULL,"
        "role TEXT NOT NULL,"
        "email TEXT UNIQUE NOT NULL,"
        "verified INTEGER NOT NULL DEFAULT 0,"
        "created_at TEXT NOT NULL"
        ")"
    ),
    "tokens": (
        "CREATE TABLE IF NOT EXISTS tokens ("
        "token_hash TEXT PRIMARY KEY,"
        "username TEXT NOT NULL,"
        "email TEXT NOT NULL,"
        "type TEXT NOT NULL,"
        "expires_at TEXT NOT NULL"
        ")"
    ),
}


def _connect(db_path: str):
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = _connect(db_path)
    cur = conn.cursor()
    for sql in DB_SCHEMA.values():
        cur.execute(sql)
    conn.commit()
    conn.close()


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def create_user(db_path: str, username: str, password_hash: str, role: str, email: str, verified: bool, created_at: datetime):
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (username, password_hash, role, email, verified, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (username, password_hash, role, email, int(bool(verified)), created_at.isoformat()),
    )
    conn.commit()
    conn.close()


def get_user(db_path: str, username: str) -> dict[str, Any] | None:
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "password_hash": row["password_hash"],
        "role": row["role"],
        "email": row["email"],
        "verified": bool(row["verified"]),
        "created_at": datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
    }


def get_user_by_email(db_path: str, email: str) -> str | None:
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT username FROM users WHERE email = ?", (email,))
    row = cur.fetchone()
    conn.close()
    return row["username"] if row else None


def update_user_verified(db_path: str, username: str, verified: bool):
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute("UPDATE users SET verified = ? WHERE username = ?", (int(bool(verified)), username))
    conn.commit()
    conn.close()


def update_user_password(db_path: str, username: str, password_hash: str):
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute("UPDATE users SET password_hash = ? WHERE username = ?", (password_hash, username))
    conn.commit()
    conn.close()


def mint_token(db_path: str, payload: dict[str, Any], expires_minutes: int, token_type: str) -> str:
    from secrets import token_urlsafe
    raw = token_urlsafe(48)
    token_hash = _hash_token(raw)
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)).isoformat()
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO tokens (token_hash, username, email, type, expires_at) VALUES (?, ?, ?, ?, ?)",
        (token_hash, payload.get("username"), payload.get("email"), token_type, expires_at),
    )
    conn.commit()
    conn.close()
    return raw


def consume_token(db_path: str, raw_token: str, token_type: str) -> dict[str, Any]:
    token_hash = _hash_token(raw_token)
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT username, email, expires_at, type FROM tokens WHERE token_hash = ?", (token_hash,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise KeyError("token not found")
    if row["type"] != token_type:
        conn.close()
        raise KeyError("token type mismatch")
    expires_at = datetime.fromisoformat(row["expires_at"])
    if datetime.now(timezone.utc) > expires_at:
        cur.execute("DELETE FROM tokens WHERE token_hash = ?", (token_hash,))
        conn.commit()
        conn.close()
        raise KeyError("token expired")
    # delete token (one-time use)
    cur.execute("DELETE FROM tokens WHERE token_hash = ?", (token_hash,))
    conn.commit()
    conn.close()
    return {"username": row["username"], "email": row["email"]}
