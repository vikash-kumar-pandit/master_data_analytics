from __future__ import annotations

import hashlib
import json
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
    "profiles": (
        "CREATE TABLE IF NOT EXISTS profiles ("
        "username TEXT PRIMARY KEY,"
        "full_name TEXT,"
        "bio TEXT,"
        "avatar_url TEXT,"
        "phone TEXT,"
        "location TEXT,"
        "preferences TEXT NOT NULL DEFAULT '{}',"
        "updated_at TEXT NOT NULL,"
        "FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE"
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
    # Ensure an index on timestamp for efficient range queries and cleanup
    try:
        cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp)")
    except Exception:
        # If the audit_log table doesn't exist yet or index creation fails, ignore
        pass
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


def get_audit_logs(
    db_path: str,
    limit: int = 100,
    offset: int = 0,
    username: str | None = None,
    event_type: str | None = None,
    status: str | None = None,
    email: str | None = None,
    client_ip: str | None = None,
    search: str | None = None,
    since: str | None = None,
    until: str | None = None,
) -> list[dict[str, Any]]:
    """Retrieve audit logs, most recent first."""
    conn = _connect(db_path)
    cur = conn.cursor()
    conditions = []
    params: list[Any] = []

    if username:
        conditions.append("username = ?")
        params.append(username)
    if event_type:
        conditions.append("event_type = ?")
        params.append(event_type)
    if status:
        conditions.append("status = ?")
        params.append(status)
    if email:
        conditions.append("email = ?")
        params.append(email)
    if client_ip:
        conditions.append("client_ip = ?")
        params.append(client_ip)
    if search:
        conditions.append(
            "(" \
            "LOWER(COALESCE(username, '')) LIKE ? OR " \
            "LOWER(COALESCE(email, '')) LIKE ? OR " \
            "LOWER(COALESCE(client_ip, '')) LIKE ? OR " \
            "LOWER(COALESCE(message, '')) LIKE ?"
            ")"
        )
        search_term = f"%{search.lower()}%"
        params.extend([search_term, search_term, search_term, search_term])
    if since:
        conditions.append("timestamp >= ?")
        params.append(since)
    if until:
        conditions.append("timestamp <= ?")
        params.append(until)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    cur.execute(
        "SELECT id, event_type, username, email, client_ip, status, message, timestamp "
        f"FROM audit_log {where_clause} ORDER BY id DESC LIMIT ? OFFSET ?",
        (*params, limit, offset),
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


def cleanup_old_audit_logs(db_path: str, days: int = 90) -> int:
    """Delete audit_log rows older than `days` days. Returns number of rows deleted."""
    if days <= 0:
        return 0
    cutoff = (datetime.now(timezone.utc) - timedelta(days=int(days))).isoformat()
    conn = _connect(db_path)
    cur = conn.cursor()
    try:
        # Use parameterized query to avoid injection and ensure correct binding
        cur.execute("DELETE FROM audit_log WHERE timestamp < ?", (cutoff,))
        deleted = cur.rowcount
        conn.commit()
    finally:
        conn.close()

    # Return the number of deleted rows for auditing
    return deleted


def get_profile(db_path: str, username: str) -> dict[str, Any] | None:
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT username, password_hash, role, email, verified, created_at FROM users WHERE username = ?",
        (username,),
    )
    user_row = cur.fetchone()
    if not user_row:
        conn.close()
        return None

    cur.execute(
        "SELECT username, full_name, bio, avatar_url, phone, location, preferences, updated_at "
        "FROM profiles WHERE username = ?",
        (username,),
    )
    profile_row = cur.fetchone()
    conn.close()

    user = {
        "username": user_row["username"],
        "password_hash": user_row["password_hash"],
        "role": user_row["role"],
        "email": user_row["email"],
        "verified": bool(user_row["verified"]),
        "created_at": datetime.fromisoformat(user_row["created_at"]) if user_row["created_at"] else None,
    }

    if not profile_row:
        return {
            **user,
            "full_name": "",
            "bio": "",
            "avatar_url": "",
            "phone": "",
            "location": "",
            "preferences": {},
            "updated_at": None,
        }

    try:
        preferences = json.loads(profile_row["preferences"] or "{}")
    except json.JSONDecodeError:
        preferences = {}

    return {
        **user,
        "full_name": profile_row["full_name"] or "",
        "bio": profile_row["bio"] or "",
        "avatar_url": profile_row["avatar_url"] or "",
        "phone": profile_row["phone"] or "",
        "location": profile_row["location"] or "",
        "preferences": preferences,
        "updated_at": profile_row["updated_at"],
    }


def upsert_profile(db_path: str, username: str, **fields) -> dict[str, Any] | None:
    allowed_fields = {"full_name", "bio", "avatar_url", "phone", "location", "preferences"}
    profile_fields = {key: value for key, value in fields.items() if key in allowed_fields and value is not None}
    if not profile_fields:
        return get_profile(db_path, username)

    if "preferences" in profile_fields:
        profile_fields["preferences"] = json.dumps(profile_fields["preferences"], ensure_ascii=False)

    updated_at = datetime.now(timezone.utc).isoformat()
    conn = _connect(db_path)
    cur = conn.cursor()
    try:
        cur.execute("SELECT username FROM users WHERE username = ?", (username,))
        if not cur.fetchone():
            conn.close()
            return None

        placeholders = ", ".join(f"{field} = ?" for field in profile_fields)
        insert_values = [username, *profile_fields.values(), updated_at]
        update_values = list(profile_fields.values())
        values = insert_values + update_values
        cur.execute(
            f"INSERT INTO profiles (username, {', '.join(profile_fields.keys())}, updated_at) "
            f"VALUES (?, {', '.join('?' for _ in profile_fields)}, ?) "
            f"ON CONFLICT(username) DO UPDATE SET {placeholders}, updated_at = excluded.updated_at",
            tuple(values),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        conn.close()
        raise
    finally:
        conn.close()

    return get_profile(db_path, username)

