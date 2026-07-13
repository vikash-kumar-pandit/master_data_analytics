from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy import or_, text
from database import SessionLocal, engine, Base
from models import User, Profile, Token, AuditLog, CatalogItem, UserActivity, MLModelRecord, WorkflowDefinition
from pipeline_engine.models import Project, PipelineNode
from profiling.models import DatasetProfile
from preparation.models import DatasetVersion, Transformation, TransformationHistory, UndoRedoStack
from copilot.models import CopilotSession, CopilotMessage, CopilotMemory
from visualization.models import DatasetVisualization

def _add_missing_columns_sqlite():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(catalog)"))
            existing_columns = {row[1] for row in result.fetchall()}
            if "ml_results" not in existing_columns:
                conn.execute(text("ALTER TABLE catalog ADD COLUMN ml_results JSON DEFAULT '{}'"))
                conn.commit()
                print("Migration: Added ml_results column to catalog table")
    except Exception as e:
        print(f"Migration check failed (expected for fresh DB): {e}")

def init_db(*args, **kwargs):
    _add_missing_columns_sqlite()
    Base.metadata.create_all(bind=engine)

def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

def create_user(db_path, username: str, password_hash: str, role: str, email: str, verified: bool, created_at: datetime):
    with SessionLocal() as db:
        user = User(
            username=username, password_hash=password_hash, role=role,
            email=email, verified=verified, created_at=created_at
        )
        db.add(user)
        db.commit()

def get_user(db_path, username: str) -> dict[str, Any] | None:
    with SessionLocal() as db:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            return None
        return {
            "username": user.username,
            "password_hash": user.password_hash,
            "role": user.role,
            "email": user.email,
            "verified": user.verified,
            "created_at": user.created_at,
        }

def get_user_by_email(db_path, email: str) -> str | None:
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).first()
        return user.username if user else None

def get_user_by_username_or_email(db_path, identifier: str) -> dict[str, Any] | None:
    with SessionLocal() as db:
        user = db.query(User).filter(
            or_(User.username.ilike(identifier), User.email.ilike(identifier))
        ).first()
        if not user: return None
        return {
            "username": user.username,
            "password_hash": user.password_hash,
            "role": user.role,
            "email": user.email,
            "verified": user.verified,
            "created_at": user.created_at,
        }

def update_user_verified(db_path, username: str, verified: bool):
    with SessionLocal() as db:
        user = db.query(User).filter(User.username == username).first()
        if user:
            user.verified = verified
            db.commit()

def update_user_password(db_path, username: str, password_hash: str):
    with SessionLocal() as db:
        user = db.query(User).filter(User.username == username).first()
        if user:
            user.password_hash = password_hash
            db.commit()

def mint_token(db_path, payload: dict[str, Any], expires_minutes: int, token_type: str) -> str:
    from secrets import token_urlsafe
    raw = token_urlsafe(48)
    token_hash = _hash_token(raw)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    with SessionLocal() as db:
        token = Token(
            token_hash=token_hash,
            username=payload.get("username"),
            email=payload.get("email"),
            type=token_type,
            expires_at=expires_at
        )
        db.add(token)
        db.commit()
    return raw

def consume_token(db_path, raw_token: str, token_type: str) -> dict[str, Any]:
    token_hash = _hash_token(raw_token)
    with SessionLocal() as db:
        token = db.query(Token).filter(Token.token_hash == token_hash).first()
        if not token:
            raise KeyError("token not found")
        if token.type != token_type:
            raise KeyError("token type mismatch")

        now = datetime.now(timezone.utc)
        expires_at = token.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if now > expires_at:
            db.delete(token)
            db.commit()
            raise KeyError("token expired")

        payload = {"username": token.username, "email": token.email}
        db.delete(token)
        db.commit()
        return payload

def log_audit_event(db_path, event_type: str, status: str, username: str | None = None, email: str | None = None, client_ip: str | None = None, message: str | None = None):
    try:
        with SessionLocal() as db:
            log = AuditLog(
                event_type=event_type, status=status, username=username,
                email=email, client_ip=client_ip, message=message
            )
            db.add(log)
            db.commit()
    except Exception as e:
        import logging
        logging.getLogger("audit").error("Failed to log audit event: %s", e)

def get_audit_logs(db_path, limit: int = 100, offset: int = 0, username: str | None = None, event_type: str | None = None, status: str | None = None, email: str | None = None, client_ip: str | None = None, search: str | None = None, since: str | None = None, until: str | None = None) -> list[dict[str, Any]]:
    with SessionLocal() as db:
        query = db.query(AuditLog)
        if username: query = query.filter(AuditLog.username == username)
        if event_type: query = query.filter(AuditLog.event_type == event_type)
        if status: query = query.filter(AuditLog.status == status)
        if email: query = query.filter(AuditLog.email == email)
        if client_ip: query = query.filter(AuditLog.client_ip == client_ip)
        if search:
            search_term = f"%{search.lower()}%"
            query = query.filter(or_(
                AuditLog.username.ilike(search_term),
                AuditLog.email.ilike(search_term),
                AuditLog.client_ip.ilike(search_term),
                AuditLog.message.ilike(search_term)
            ))
        if since: query = query.filter(AuditLog.timestamp >= since)
        if until: query = query.filter(AuditLog.timestamp <= until)

        logs = query.order_by(AuditLog.id.desc()).offset(offset).limit(limit).all()
        return [{
            "id": l.id, "event_type": l.event_type, "username": l.username,
            "email": l.email, "client_ip": l.client_ip, "status": l.status,
            "message": l.message, "timestamp": l.timestamp.isoformat() if l.timestamp else None
        } for l in logs]

def get_audit_logs_for_user(db_path, username: str, limit: int = 50) -> list[dict[str, Any]]:
    return get_audit_logs(db_path, limit=limit, username=username)

def cleanup_old_audit_logs(db_path, days: int = 90) -> int:
    if days <= 0: return 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    with SessionLocal() as db:
        deleted = db.query(AuditLog).filter(AuditLog.timestamp < cutoff).delete()
        db.commit()
        return deleted

def get_profile(db_path, username: str) -> dict[str, Any] | None:
    with SessionLocal() as db:
        user = db.query(User).filter(User.username == username).first()
        if not user: return None

        base_user = {
            "username": user.username,
            "password_hash": user.password_hash,
            "role": user.role,
            "email": user.email,
            "verified": user.verified,
            "created_at": user.created_at,
        }

        profile = user.profile
        if not profile:
            return {**base_user, "full_name": "", "bio": "", "avatar_url": "", "phone": "", "location": "", "preferences": {}, "updated_at": None}

        return {
            **base_user,
            "full_name": profile.full_name or "",
            "bio": profile.bio or "",
            "avatar_url": profile.avatar_url or "",
            "phone": profile.phone or "",
            "location": profile.location or "",
            "preferences": profile.preferences or {},
            "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
        }

def upsert_profile(db_path, username: str, **fields) -> dict[str, Any] | None:
    allowed_fields = {"full_name", "bio", "avatar_url", "phone", "location", "preferences"}
    profile_fields = {k: v for k, v in fields.items() if k in allowed_fields and v is not None}

    with SessionLocal() as db:
        user = db.query(User).filter(User.username == username).first()
        if not user: return None

        if not user.profile:
            profile = Profile(username=username, **profile_fields)
            db.add(profile)
        else:
            for k, v in profile_fields.items():
                setattr(user.profile, k, v)
        db.commit()

    return get_profile(db_path, username)
