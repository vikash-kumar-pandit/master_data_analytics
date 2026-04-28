from __future__ import annotations

import hashlib
import logging
import os
import re
import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from typing import Any

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
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
MAX_RESET_ATTEMPTS = int(os.getenv("AUTH_MAX_RESET_ATTEMPTS", "5"))
RESET_WINDOW_MINUTES = int(os.getenv("AUTH_RESET_WINDOW_MINUTES", "30"))
VERIFY_TOKEN_EXPIRE_MINUTES = int(os.getenv("AUTH_VERIFY_TOKEN_EXPIRE_MINUTES", "1440"))
RESET_TOKEN_EXPIRE_MINUTES = int(os.getenv("AUTH_RESET_TOKEN_EXPIRE_MINUTES", "30"))
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:5173")
APP_ENV = os.getenv("APP_ENV", "development").lower()
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM = os.getenv("SMTP_FROM", "noreply@datasaas.local")
IS_PRODUCTION = APP_ENV == "production"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
auth_router = APIRouter(tags=["auth"])
logger = logging.getLogger("auth")


# Demo users for local development. Replace with DB-backed users in production.
_SEED_USERS = {
    "admin_user": {"password": "password123", "role": "admin", "email": "admin@datasaas.local", "verified": True},
    "data_analyst": {
        "password": "password123",
        "role": "analyst",
        "email": "analyst@datasaas.local",
        "verified": True,
    },
    "guest_viewer": {
        "password": "password123",
        "role": "viewer",
        "email": "viewer@datasaas.local",
        "verified": True,
    },
}

USERS_DB = {
    username: {
        "password_hash": pwd_context.hash(user["password"]),
        "role": user["role"],
        "email": user["email"],
        "verified": user.get("verified", False),
        "created_at": datetime.now(timezone.utc),
    }
    for username, user in _SEED_USERS.items()
}

_LOGIN_ATTEMPTS: dict[str, list[datetime]] = {}
_REGISTER_ATTEMPTS: dict[str, list[datetime]] = {}
_RESET_ATTEMPTS: dict[str, list[datetime]] = {}
_VERIFY_TOKENS: dict[str, dict[str, Any]] = {}
_RESET_TOKENS: dict[str, dict[str, Any]] = {}


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)
    email: str = Field(min_length=5, max_length=254)
    role: str = Field(default="viewer")


class ResendVerificationRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)


class PasswordResetRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)


class PasswordResetConfirmRequest(BaseModel):
    token: str = Field(min_length=16, max_length=512)
    new_password: str = Field(min_length=8, max_length=128)


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


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _mint_token(store: dict[str, dict[str, Any]], payload: dict[str, Any], expires_minutes: int) -> str:
    raw_token = secrets.token_urlsafe(48)
    token_hash = _hash_token(raw_token)
    store[token_hash] = {
        **payload,
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=expires_minutes),
    }
    return raw_token


def _consume_token(store: dict[str, dict[str, Any]], raw_token: str) -> dict[str, Any]:
    token_hash = _hash_token(raw_token)
    payload = store.pop(token_hash, None)
    if not payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")
    if datetime.now(timezone.utc) > payload["expires_at"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token expired")
    return payload


def _find_username_by_email(email: str) -> str | None:
    for username, user in USERS_DB.items():
        if user.get("email") == email:
            return username
    return None


def _validate_username(username: str) -> str:
    normalized = username.strip().lower()
    if not re.fullmatch(r"[a-z0-9_\-.]{3,64}", normalized):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username must be 3-64 chars and contain only letters, numbers, underscore, hyphen, or dot",
        )
    return normalized


def _validate_email(email: str) -> str:
    normalized = email.strip().lower()
    if not re.fullmatch(r"[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,63}", normalized):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email address")
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


def _send_email(to_email: str, subject: str, body: str):
    if not SMTP_HOST:
        logger.info("Email provider not configured. Simulated email to %s subject=%s", to_email, subject)
        logger.info("Email content: %s", body)
        return

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = SMTP_FROM
    message["To"] = to_email
    message.set_content(body)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
        smtp.starttls()
        if SMTP_USER and SMTP_PASSWORD:
            smtp.login(SMTP_USER, SMTP_PASSWORD)
        smtp.send_message(message)


def _send_verification_email(username: str, email: str, token: str):
    verify_link = f"{APP_BASE_URL}/login?verify_token={token}"
    body = (
        f"Hello {username},\n\n"
        "Welcome to DataSaaS Pro. Please verify your email by clicking this link:\n"
        f"{verify_link}\n\n"
        f"This link expires in {VERIFY_TOKEN_EXPIRE_MINUTES} minutes."
    )
    _send_email(email, "Verify your DataSaaS account", body)


def _send_password_reset_email(username: str, email: str, token: str):
    reset_link = f"{APP_BASE_URL}/login?reset_token={token}"
    body = (
        f"Hello {username},\n\n"
        "A password reset was requested for your account. Use this link to reset your password:\n"
        f"{reset_link}\n\n"
        f"This link expires in {RESET_TOKEN_EXPIRE_MINUTES} minutes."
    )
    _send_email(email, "Reset your DataSaaS password", body)


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

    if not user.get("verified", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email is not verified")

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
    email = _validate_email(payload.email)
    role = _validate_role(payload.role)
    _validate_password_strength(payload.password)

    client_key = _get_client_id(request, email)
    attempts = _prune_attempts(_REGISTER_ATTEMPTS, client_key, REGISTER_WINDOW_MINUTES)
    if len(attempts) >= MAX_REGISTER_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many registration attempts. Try again in {REGISTER_WINDOW_MINUTES} minutes",
        )

    if username in USERS_DB or _find_username_by_email(email):
        _record_attempt(_REGISTER_ATTEMPTS, client_key)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Account already exists")

    USERS_DB[username] = {
        "password_hash": pwd_context.hash(payload.password),
        "role": role,
        "email": email,
        "verified": False,
        "created_at": datetime.now(timezone.utc),
    }

    _REGISTER_ATTEMPTS.pop(client_key, None)
    verify_token = _mint_token(_VERIFY_TOKENS, {"username": username, "email": email}, VERIFY_TOKEN_EXPIRE_MINUTES)
    _send_verification_email(username, email, verify_token)

    response: dict[str, Any] = {
        "message": "Registration successful. Please verify your email before login.",
        "verification_required": True,
    }
    if not IS_PRODUCTION:
        response["verification_token"] = verify_token
    return response


@auth_router.get("/verify-email")
async def verify_email(token: str = Query(..., min_length=16)) -> dict[str, Any]:
    payload = _consume_token(_VERIFY_TOKENS, token)
    username = payload.get("username")
    user = USERS_DB.get(username)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Account not found")

    user["verified"] = True
    return {"message": "Email verified successfully. You can now sign in."}


@auth_router.post("/resend-verification")
async def resend_verification(payload: ResendVerificationRequest, request: Request) -> dict[str, Any]:
    email = _validate_email(payload.email)
    client_key = _get_client_id(request, email)
    attempts = _prune_attempts(_REGISTER_ATTEMPTS, client_key, REGISTER_WINDOW_MINUTES)
    if len(attempts) >= MAX_REGISTER_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many requests. Try again in {REGISTER_WINDOW_MINUTES} minutes",
        )

    username = _find_username_by_email(email)
    if not username:
        return {"message": "If the email exists, a verification link has been sent."}

    user = USERS_DB.get(username, {})
    if user.get("verified", False):
        return {"message": "Email is already verified."}

    verify_token = _mint_token(_VERIFY_TOKENS, {"username": username, "email": email}, VERIFY_TOKEN_EXPIRE_MINUTES)
    _send_verification_email(username, email, verify_token)

    response: dict[str, Any] = {"message": "Verification email sent."}
    if not IS_PRODUCTION:
        response["verification_token"] = verify_token
    return response


@auth_router.post("/password-reset/request")
async def request_password_reset(payload: PasswordResetRequest, request: Request) -> dict[str, Any]:
    email = _validate_email(payload.email)
    client_key = _get_client_id(request, email)
    attempts = _prune_attempts(_RESET_ATTEMPTS, client_key, RESET_WINDOW_MINUTES)
    if len(attempts) >= MAX_RESET_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many password reset attempts. Try again in {RESET_WINDOW_MINUTES} minutes",
        )

    _record_attempt(_RESET_ATTEMPTS, client_key)
    username = _find_username_by_email(email)
    if not username:
        return {"message": "If an account exists, a password reset link has been sent."}

    user = USERS_DB.get(username, {})
    if not user.get("verified", False):
        return {"message": "If an account exists, a password reset link has been sent."}

    reset_token = _mint_token(_RESET_TOKENS, {"username": username, "email": email}, RESET_TOKEN_EXPIRE_MINUTES)
    _send_password_reset_email(username, email, reset_token)

    response: dict[str, Any] = {"message": "If an account exists, a password reset link has been sent."}
    if not IS_PRODUCTION:
        response["reset_token"] = reset_token
    return response


@auth_router.post("/password-reset/confirm")
async def confirm_password_reset(payload: PasswordResetConfirmRequest) -> dict[str, Any]:
    _validate_password_strength(payload.new_password)
    token_payload = _consume_token(_RESET_TOKENS, payload.token)
    username = token_payload.get("username")
    user = USERS_DB.get(username)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Account not found")

    user["password_hash"] = pwd_context.hash(payload.new_password)
    return {"message": "Password reset successful. You can now sign in."}


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
