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
    "audit_log": (
        "CREATE TABLE IF NOT EXISTS audit_log ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "event_type TEXT NOT NULL,"
        "username TEXT,"
        "email TEXT,"
        "client_ip TEXT,"
        "status TEXT NOT NULL,"
        "message TEXT,"
        "timestamp TEXT NOT NULL"
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


def log_audit_event(
    db_path: str,
    event_type: str,
    status: str,
    username: str | None = None,
    email: str | None = None,
    client_ip: str | None = None,
    message: str | None = None,
):
    """Log an audit event to the audit_log table."""
    try:
        conn = _connect(db_path)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO audit_log (event_type, username, email, client_ip, status, message, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                event_type,
                username,
                email,
                client_ip,
                status,
                message,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        # Log errors to console but don't fail the operation
        import logging
        logging.getLogger("audit").error("Failed to log audit event: %s", e)


def get_audit_logs(db_path: str, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
    """Retrieve audit logs, most recent first."""
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, event_type, username, email, client_ip, status, message, timestamp "
        "FROM audit_log ORDER BY id DESC LIMIT ? OFFSET ?",
        (limit, offset),
    )
    rows = cur.fetchall()
    conn.close()
    
    return [
        {
            "id": row["id"],
            "event_type": row["event_type"],
            "username": row["username"],
            "email": row["email"],
            "client_ip": row["client_ip"],
            "status": row["status"],
            "message": row["message"],
            "timestamp": row["timestamp"],
        }
        for row in rows
    ]


def get_audit_logs_for_user(db_path: str, username: str, limit: int = 50) -> list[dict[str, Any]]:
    """Retrieve audit logs for a specific user."""
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, event_type, username, email, client_ip, status, message, timestamp "
        "FROM audit_log WHERE username = ? ORDER BY id DESC LIMIT ?",
        (username, limit),
    )
    rows = cur.fetchall()
    conn.close()
    
    return [
        {
            "id": row["id"],
            "event_type": row["event_type"],
            "username": row["username"],
            "email": row["email"],
            "client_ip": row["client_ip"],
            "status": row["status"],
            "message": row["message"],
            "timestamp": row["timestamp"],
        }
        for row in rows
    ]
