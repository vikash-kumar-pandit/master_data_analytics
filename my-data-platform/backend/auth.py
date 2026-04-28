from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from pydantic import BaseModel, Field


SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-this-in-production-please-use-a-strong-32plus-char-secret")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "2"))
MAX_LOGIN_ATTEMPTS = int(os.getenv("AUTH_MAX_LOGIN_ATTEMPTS", "5"))
LOGIN_WINDOW_MINUTES = int(os.getenv("AUTH_LOGIN_WINDOW_MINUTES", "15"))
MAX_REGISTER_ATTEMPTS = int(os.getenv("AUTH_MAX_REGISTER_ATTEMPTS", "5"))
REGISTER_WINDOW_MINUTES = int(os.getenv("AUTH_REGISTER_WINDOW_MINUTES", "30"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
auth_router = APIRouter(tags=["auth"])


# Demo users for local development. Replace with DB-backed users in production.
_SEED_USERS = {
    "admin_user": {"password": "password123", "role": "admin"},
    "data_analyst": {"password": "password123", "role": "analyst"},
    "guest_viewer": {"password": "password123", "role": "viewer"},
}

USERS_DB = {
    username: {
        "password_hash": pwd_context.hash(user["password"]),
        "role": user["role"],
    }
    for username, user in _SEED_USERS.items()
}

_LOGIN_ATTEMPTS: dict[str, list[datetime]] = {}
_REGISTER_ATTEMPTS: dict[str, list[datetime]] = {}


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(default="viewer")


def _get_client_id(request: Request, username: str) -> str:
    client_ip = request.client.host if request.client else "unknown"
    return f"{client_ip}:{username.lower()}"


def _prune_attempts(bucket: dict[str, list[datetime]], key: str, window_minutes: int) -> list[datetime]:
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(minutes=window_minutes)
    attempts = [ts for ts in bucket.get(key, []) if ts >= window_start]
    bucket[key] = attempts
    return attempts


def _record_attempt(bucket: dict[str, list[datetime]], key: str):
    now = datetime.now(timezone.utc)
    bucket.setdefault(key, []).append(now)


def _validate_username(username: str) -> str:
    normalized = username.strip().lower()
    if not re.fullmatch(r"[a-z0-9_\-.]{3,64}", normalized):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username must be 3-64 chars and contain only letters, numbers, underscore, hyphen, or dot",
        )
    return normalized


def _validate_password_strength(password: str):
    if len(password) < 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must be at least 8 characters")
    if len(password) > 128:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must be <= 128 characters")
    if not re.search(r"[A-Z]", password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must contain an uppercase letter")
    if not re.search(r"[a-z]", password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must contain a lowercase letter")
    if not re.search(r"\d", password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must contain a number")
    if not re.search(r"[^A-Za-z0-9]", password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must contain a special character")


def _validate_role(role: str) -> str:
    # Public self-registration is restricted to non-admin roles.
    allowed = {"viewer", "analyst"}
    normalized = role.strip().lower()
    if normalized not in allowed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role for registration")
    return normalized


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


def create_access_token(subject: str, role: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    token_data = {
        "sub": subject,
        "role": role,
        "exp": expires_at,
    }
    return jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

    username = payload.get("sub")
    role = payload.get("role")
    if not username or not role:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    return {"username": username, "role": role}


@auth_router.post("/login")
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()) -> dict[str, Any]:
    username = _validate_username(form_data.username)
    client_key = _get_client_id(request, username)
    attempts = _prune_attempts(_LOGIN_ATTEMPTS, client_key, LOGIN_WINDOW_MINUTES)
    if len(attempts) >= MAX_LOGIN_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many login attempts. Try again in {LOGIN_WINDOW_MINUTES} minutes",
        )

    user = USERS_DB.get(username)
    if not user or not verify_password(form_data.password, user["password_hash"]):
        _record_attempt(_LOGIN_ATTEMPTS, client_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    _LOGIN_ATTEMPTS.pop(client_key, None)
    token = create_access_token(username, user["role"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user["role"],
        "username": username,
        "expires_in": TOKEN_EXPIRE_HOURS * 3600,
    }


@auth_router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, request: Request) -> dict[str, Any]:
    username = _validate_username(payload.username)
    role = _validate_role(payload.role)
    _validate_password_strength(payload.password)

    client_key = _get_client_id(request, username)
    attempts = _prune_attempts(_REGISTER_ATTEMPTS, client_key, REGISTER_WINDOW_MINUTES)
    if len(attempts) >= MAX_REGISTER_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many registration attempts. Try again in {REGISTER_WINDOW_MINUTES} minutes",
        )

    if username in USERS_DB:
        _record_attempt(_REGISTER_ATTEMPTS, client_key)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")

    USERS_DB[username] = {
        "password_hash": pwd_context.hash(payload.password),
        "role": role,
    }

    _REGISTER_ATTEMPTS.pop(client_key, None)
    token = create_access_token(username, role)
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": role,
        "username": username,
        "expires_in": TOKEN_EXPIRE_HOURS * 3600,
    }


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict[str, Any]:
    try:
        return decode_access_token(token)
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc


@auth_router.get("/me")
async def get_me(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    return current_user


def require_role(allowed_roles: list[str]):
    allowed = set(allowed_roles)

    def role_checker(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
        if current_user["role"] not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation not permitted for this role",
            )
        return current_user

    return role_checker
