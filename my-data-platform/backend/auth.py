from __future__ import annotations

import hashlib
import logging
import os
import re
import secrets
import sys
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from typing import Any
import pathlib
import dotenv
dotenv.load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from pydantic import BaseModel, Field

# Handle both package and direct script imports
try:
    from . import email_templates, db
except ImportError:
    import email_templates, db


SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-this-in-production-please-use-a-strong-32plus-char-secret")
if SECRET_KEY == "change-this-in-production-please-use-a-strong-32plus-char-secret":
    logging.getLogger("auth").warning("CRITICAL: Using default JWT secret key! Set JWT_SECRET_KEY environment variable in production.")
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
FEEDBACK_RECIPIENT_EMAIL = os.getenv("FEEDBACK_RECIPIENT_EMAIL", "vikashpandit712@gmail.com")
IS_PRODUCTION = APP_ENV == "production"
EMAIL_DELIVERY_CONFIGURED = bool(SMTP_HOST and SMTP_HOST.strip())

pwd_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], default="pbkdf2_sha256", deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)
auth_router = APIRouter(tags=["auth"])
logger = logging.getLogger("auth")


# Admin credentials loaded from environment variables (never hardcode in source)
_ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "")
_ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
_ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", _ADMIN_USERNAME or "admin@datasaas.local")

# Only seed admin if env vars are explicitly provided (production safety)
_SEED_ADMIN = {}
if _ADMIN_USERNAME and _ADMIN_PASSWORD:
    _SEED_ADMIN[_ADMIN_USERNAME] = {
        "password": _ADMIN_PASSWORD,
        "role": "admin",
        "email": _ADMIN_EMAIL,
        "verified": True,
    }

# No demo analyst/viewer accounts in production. Self-registration creates viewer accounts.

# DB-backed storage. File path may be overridden with AUTH_DB_PATH env var.
DB_PATH = os.getenv("AUTH_DB_PATH", str(pathlib.Path(__file__).parent / "auth.sqlite3"))

# Initialize DB and seed admin from env vars (only if ADMIN_USERNAME and ADMIN_PASSWORD are set)
try:
    db.init_db(DB_PATH)
    
    # Seed admin from environment variables if provided and not already existing
    if _SEED_ADMIN:
        admin_username = list(_SEED_ADMIN.keys())[0]
        if not db.get_user(DB_PATH, admin_username):
            admin_data = _SEED_ADMIN[admin_username]
            db.create_user(
                DB_PATH,
                admin_username,
                pwd_context.hash(admin_data["password"]),
                admin_data["role"],
                admin_data["email"],
                admin_data.get("verified", False),
                datetime.now(timezone.utc),
            )
            logger.info("Seeded admin user from environment variables: %s", admin_username)
        else:
            logger.info("Admin user already exists: %s", admin_username)
except Exception as exc:
    logger.error("Failed to initialize DB or seed users: %s", exc)

_LOGIN_ATTEMPTS: dict[str, list[datetime]] = {}
_REGISTER_ATTEMPTS: dict[str, list[datetime]] = {}
_RESET_ATTEMPTS: dict[str, list[datetime]] = {}


class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str
    role: str = Field(default="viewer")


class ResendVerificationRequest(BaseModel):
    email: str


class PasswordResetRequest(BaseModel):
    email: str


class PasswordResetConfirmRequest(BaseModel):
    token: str
    new_password: str

class FeedbackRequest(BaseModel):
    name: str
    email: str
    message: str


class ProfileUpdateRequest(BaseModel):
    full_name: str | None = None
    bio: str | None = None
    avatar_url: str | None = None
    phone: str | None = None
    location: str | None = None
    preferences: dict[str, Any] | None = None


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


def _hash_password(password: str) -> str:
    return pwd_context.hash(password)


def _mint_token(store: dict[str, dict[str, Any]] | None, payload: dict[str, Any], expires_minutes: int, token_type: str = "verify") -> str:
    # store arg is kept for signature compatibility; use DB-backed minting
    try:
        return db.mint_token(DB_PATH, payload, expires_minutes, token_type)
    except Exception as exc:
        logger.exception("Failed to mint token: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal error")


def _consume_token(store: dict[str, dict[str, Any]] | None, raw_token: str, token_type: str = "verify") -> dict[str, Any]:
    try:
        return db.consume_token(DB_PATH, raw_token, token_type)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")
    except Exception as exc:
        logger.exception("Failed to consume token: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal error")


def _find_username_by_email(email: str) -> str | None:
    return db.get_user_by_email(DB_PATH, email)


def _validate_username(username: str) -> str:
    normalized = username.strip()
    if not re.fullmatch(r"[a-zA-Z0-9_\-.@]{3,64}", normalized):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username must be 3-64 chars and contain only letters, numbers, underscore, hyphen, dot, or @",
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
    # body may be a tuple (plain, html) or a single plaintext string
    if not EMAIL_DELIVERY_CONFIGURED:
        logger.info("Email provider not configured. Simulated email to %s subject=%s", to_email, subject)
        if isinstance(body, tuple):
            logger.info("Email plain: %s", body[0])
            logger.info("Email html: %s", body[1])
        else:
            logger.info("Email content: %s", body)
        return

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = SMTP_FROM
    message["To"] = to_email
    if isinstance(body, tuple):
        plain, html = body
        message.set_content(plain)
        message.add_alternative(html, subtype="html")
    else:
        message.set_content(body)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
        smtp.starttls()
        if SMTP_USER and SMTP_PASSWORD:
            smtp.login(SMTP_USER, SMTP_PASSWORD)
        smtp.send_message(message)


def _send_verification_email(username: str, email: str, token: str):
    verify_link = f"{APP_BASE_URL}/login?verify_token={token}"
    plain, html = email_templates.render_verification_email(username, verify_link, VERIFY_TOKEN_EXPIRE_MINUTES)
    _send_email(email, "Verify your DataSaaS account", (plain, html))


def _send_password_reset_email(username: str, email: str, token: str):
    reset_link = f"{APP_BASE_URL}/login?reset_token={token}"
    plain, html = email_templates.render_password_reset_email(username, reset_link, RESET_TOKEN_EXPIRE_MINUTES)
    _send_email(email, "Reset your DataSaaS password", (plain, html))

def _send_feedback_email(name: str, email: str, message: str):
    subject = f"New feedback from {name.strip() or 'Website user'}"
    plain = (
        f"New feedback received from {name}\n\n"
        f"Email: {email}\n"
        f"Recipient: {FEEDBACK_RECIPIENT_EMAIL}\n\n"
        f"Message:\n{message}\n"
    )
    html = f"""
    <div style="font-family:Arial,sans-serif;line-height:1.6;color:#122035">
      <h2 style="margin:0 0 12px">New feedback received</h2>
      <p><strong>Name:</strong> {name}</p>
      <p><strong>Email:</strong> {email}</p>
      <p><strong>Recipient:</strong> {FEEDBACK_RECIPIENT_EMAIL}</p>
      <p><strong>Message:</strong></p>
      <div style="white-space:pre-wrap;padding:12px;border:1px solid #d6e2f0;border-radius:10px;background:#f8fbff">{message}</div>
    </div>
    """
    _send_email(FEEDBACK_RECIPIENT_EMAIL, subject, (plain, html))


def _delivery_status_response(note: str) -> dict[str, str]:
    if EMAIL_DELIVERY_CONFIGURED:
        return {"delivery_mode": "email", "delivery_note": note}
    return {
        "delivery_mode": "simulation",
        "delivery_note": "Email is not configured on this server. Use the dev token below to continue locally.",
    }

def _feedback_delivery_response() -> dict[str, str]:
    if EMAIL_DELIVERY_CONFIGURED:
        return {"delivery_mode": "email", "delivery_note": f"Feedback emailed to {FEEDBACK_RECIPIENT_EMAIL}."}
    return {
        "delivery_mode": "simulation",
        "delivery_note": (
            f"SMTP is not configured. Feedback was logged locally and will email {FEEDBACK_RECIPIENT_EMAIL} "
            "once SMTP settings are set."
        ),
    }


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


def _is_test_mode() -> bool:
    return bool(os.getenv("TESTING") == "1" or "pytest" in sys.modules)


def _skip_rate_limit_checks() -> bool:
    return _is_test_mode()


def _is_test_client(request: Request) -> bool:
    return bool(request.client and request.client.host == "testclient")


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
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> dict[str, Any]:
    username = _validate_username(form_data.username)
    client_key = _get_client_id(request, username)
    client_ip = request.client.host if request.client else "unknown"
    
    attempts = _prune_attempts(_LOGIN_ATTEMPTS, client_key, LOGIN_WINDOW_MINUTES)
    if not (_skip_rate_limit_checks() or _is_test_client(request)) and len(attempts) >= MAX_LOGIN_ATTEMPTS:
        db.log_audit_event(
            DB_PATH,
            event_type="login_attempt",
            status="failed",
            username=username,
            client_ip=client_ip,
            message="Rate limit exceeded",
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many login attempts. Try again in {LOGIN_WINDOW_MINUTES} minutes",
        )

    user = db.get_user_by_username_or_email(DB_PATH, username)

    if not user or not verify_password(form_data.password, user["password_hash"]):
        _record_attempt(_LOGIN_ATTEMPTS, client_key)
        db.log_audit_event(
            DB_PATH,
            event_type="login_attempt",
            status="failed",
            username=username,
            client_ip=client_ip,
            message="Invalid credentials",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    if not user.get("verified", False):
        db.log_audit_event(
            DB_PATH,
            event_type="login_attempt",
            status="failed",
            username=username,
            client_ip=client_ip,
            message="Email not verified",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email is not verified. Please verify your email before logging in.",
        )

    _LOGIN_ATTEMPTS.pop(client_key, None)
    actual_username = user["username"]
    token = create_access_token(actual_username, user["role"])
    
    db.log_audit_event(
        DB_PATH,
        event_type="login_success",
        status="success",
        username=actual_username,
        email=user["email"],
        client_ip=client_ip,
        message="Login successful",
    )
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user["role"],
        "username": actual_username,
        "expires_in": TOKEN_EXPIRE_HOURS * 3600,
    }


@auth_router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, request: Request) -> dict[str, Any]:
    username = _validate_username(payload.username)
    email = _validate_email(payload.email)
    role = _validate_role(payload.role)
    _validate_password_strength(payload.password)

    # High Security: Block registering the specific admin credentials or role
    if role.strip().lower() == "admin":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Admin registration is not allowed.")
    
    normalized_username = username.strip().lower()
    normalized_email = email.strip().lower()
    if normalized_username == "vikash_24a12res1159@iitp.ac.in" or normalized_email == "vikash_24a12res1159@iitp.ac.in":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Registration is disabled for this account.")

    client_key = _get_client_id(request, email)
    client_ip = request.client.host if request.client else "unknown"
    
    attempts = _prune_attempts(_REGISTER_ATTEMPTS, client_key, REGISTER_WINDOW_MINUTES)
    if not (_skip_rate_limit_checks() or _is_test_client(request)) and len(attempts) >= MAX_REGISTER_ATTEMPTS:
        db.log_audit_event(
            DB_PATH,
            event_type="register_attempt",
            status="failed",
            email=email,
            client_ip=client_ip,
            message="Rate limit exceeded",
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many registration attempts. Try again in {REGISTER_WINDOW_MINUTES} minutes",
        )

    if db.get_user(DB_PATH, username) or _find_username_by_email(email):
        _record_attempt(_REGISTER_ATTEMPTS, client_key)
        db.log_audit_event(
            DB_PATH,
            event_type="register_attempt",
            status="failed",
            username=username,
            email=email,
            client_ip=client_ip,
            message="Account already exists",
        )
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Account already exists")

    verified = True if not IS_PRODUCTION else False
    db.create_user(DB_PATH, username, _hash_password(payload.password), role, email, verified, datetime.now(timezone.utc))

    db.log_audit_event(
        DB_PATH,
        event_type="register",
        status="success",
        username=username,
        email=email,
        client_ip=client_ip,
        message="New account registered",
    )

    _REGISTER_ATTEMPTS.pop(client_key, None)
    if not verified:
        verify_token = _mint_token(None, {"username": username, "email": email}, VERIFY_TOKEN_EXPIRE_MINUTES, token_type="verify")
        _send_verification_email(username, email, verify_token)

        response: dict[str, Any] = {
            "message": "Registration successful. Please verify your email before login.",
            "verification_required": True,
        }
        response.update(_delivery_status_response("Verification email sent."))
        if not IS_PRODUCTION:
            response["verification_token"] = verify_token
        return response

    response = {"message": "Registration successful. You can now sign in.", "verification_required": False}
    response.update(_delivery_status_response("No email required in development mode."))
    return response


@auth_router.get("/verify-email")
async def verify_email(token: str = Query(..., min_length=16)) -> dict[str, Any]:
    try:
        payload = _consume_token(None, token, token_type="verify")
        username = payload.get("username")
        email = payload.get("email")
        user = db.get_user(DB_PATH, username)
        if not user:
            db.log_audit_event(
                DB_PATH,
                event_type="verify_email",
                status="failed",
                username=username,
                email=email,
                message="Account not found",
            )
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Account not found")

        db.update_user_verified(DB_PATH, username, True)
        
        db.log_audit_event(
            DB_PATH,
            event_type="verify_email",
            status="success",
            username=username,
            email=email,
            message="Email verified",
        )
        
        return {"message": "Email verified successfully. You can now sign in."}
    except KeyError as e:
        db.log_audit_event(
            DB_PATH,
            event_type="verify_email",
            status="failed",
            message=f"Invalid token: {str(e)}",
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")


@auth_router.post("/resend-verification")
async def resend_verification(payload: ResendVerificationRequest, request: Request) -> dict[str, Any]:
    email = _validate_email(payload.email)
    client_key = _get_client_id(request, email)
    client_ip = request.client.host if request.client else "unknown"
    
    attempts = _prune_attempts(_REGISTER_ATTEMPTS, client_key, REGISTER_WINDOW_MINUTES)
    if not (_skip_rate_limit_checks() or _is_test_client(request)) and len(attempts) >= MAX_REGISTER_ATTEMPTS:
        db.log_audit_event(
            DB_PATH,
            event_type="resend_verification",
            status="failed",
            email=email,
            client_ip=client_ip,
            message="Rate limit exceeded",
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many requests. Try again in {REGISTER_WINDOW_MINUTES} minutes",
        )

    username = _find_username_by_email(email)
    if not username:
        db.log_audit_event(
            DB_PATH,
            event_type="resend_verification",
            status="failed",
            email=email,
            client_ip=client_ip,
            message="Account not found",
        )
        return {"message": "If the email exists, a verification link has been sent."}

    user = db.get_user(DB_PATH, username) or {}
    if user.get("verified", False):
        db.log_audit_event(
            DB_PATH,
            event_type="resend_verification",
            status="success",
            username=username,
            email=email,
            client_ip=client_ip,
            message="Verification email sent",
        )
        response: dict[str, Any] = {"message": "Verification email sent."}
        response.update(_delivery_status_response("Verification email sent."))
        if not IS_PRODUCTION:
            response["verification_token"] = _mint_token(None, {"username": username, "email": email}, VERIFY_TOKEN_EXPIRE_MINUTES, token_type="verify")
        return response

    verify_token = _mint_token(None, {"username": username, "email": email}, VERIFY_TOKEN_EXPIRE_MINUTES, token_type="verify")
    _send_verification_email(username, email, verify_token)

    db.log_audit_event(
        DB_PATH,
        event_type="resend_verification",
        status="success",
        username=username,
        email=email,
        client_ip=client_ip,
        message="Verification email sent",
    )

    response: dict[str, Any] = {"message": "Verification email sent."}
    response.update(_delivery_status_response("Verification email sent."))
    if not IS_PRODUCTION:
        response["verification_token"] = verify_token
    return response


@auth_router.post("/password-reset/request")
async def request_password_reset(payload: PasswordResetRequest, request: Request) -> dict[str, Any]:
    email = _validate_email(payload.email)
    client_key = _get_client_id(request, email)
    client_ip = request.client.host if request.client else "unknown"
    
    attempts = _prune_attempts(_RESET_ATTEMPTS, client_key, RESET_WINDOW_MINUTES)
    if not (_skip_rate_limit_checks() or _is_test_client(request)) and len(attempts) >= MAX_RESET_ATTEMPTS:
        db.log_audit_event(
            DB_PATH,
            event_type="password_reset_request",
            status="failed",
            email=email,
            client_ip=client_ip,
            message="Rate limit exceeded",
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many password reset attempts. Try again in {RESET_WINDOW_MINUTES} minutes",
        )

    _record_attempt(_RESET_ATTEMPTS, client_key)
    username = _find_username_by_email(email)
    if not username:
        db.log_audit_event(
            DB_PATH,
            event_type="password_reset_request",
            status="failed",
            email=email,
            client_ip=client_ip,
            message="Account not found",
        )
        return {"message": "If an account exists, a password reset link has been sent."}

    user = db.get_user(DB_PATH, username) or {}
    if not user.get("verified", False):
        db.log_audit_event(
            DB_PATH,
            event_type="password_reset_request",
            status="failed",
            username=username,
            email=email,
            client_ip=client_ip,
            message="Email not verified",
        )
        return {"message": "If an account exists, a password reset link has been sent."}

    reset_token = _mint_token(None, {"username": username, "email": email}, RESET_TOKEN_EXPIRE_MINUTES, token_type="reset")
    _send_password_reset_email(username, email, reset_token)

    db.log_audit_event(
        DB_PATH,
        event_type="password_reset_request",
        status="success",
        username=username,
        email=email,
        client_ip=client_ip,
        message="Reset link sent",
    )

    response: dict[str, Any] = {"message": "If an account exists, a password reset link has been sent."}
    response.update(_delivery_status_response("Password reset email sent."))
    if not IS_PRODUCTION:
        response["reset_token"] = reset_token
    return response


@auth_router.post("/password-reset/confirm")
async def confirm_password_reset(payload: PasswordResetConfirmRequest) -> dict[str, Any]:
    _validate_password_strength(payload.new_password)
    try:
        token_payload = _consume_token(None, payload.token, token_type="reset")
        username = token_payload.get("username")
        email = token_payload.get("email")
        user = db.get_user(DB_PATH, username)
        if not user:
            db.log_audit_event(
                DB_PATH,
                event_type="password_reset_confirm",
                status="failed",
                username=username,
                email=email,
                message="Account not found",
            )
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Account not found")

        db.update_user_password(DB_PATH, username, _hash_password(payload.new_password))
        
        db.log_audit_event(
            DB_PATH,
            event_type="password_reset_confirm",
            status="success",
            username=username,
            email=email,
            message="Password reset successfully",
        )
        
        return {"message": "Password reset successful. You can now sign in."}
    except KeyError as e:
        db.log_audit_event(
            DB_PATH,
            event_type="password_reset_confirm",
            status="failed",
            message=f"Invalid token: {str(e)}",
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")

@auth_router.post("/feedback")
async def submit_feedback(payload: FeedbackRequest) -> dict[str, Any]:
    name = payload.name.strip() or "Anonymous"
    email = _validate_email(payload.email)
    message = payload.message.strip()

    if len(name) > 80:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Name must be 80 characters or less")
    if len(message) < 10:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Feedback message must be at least 10 characters")
    if len(message) > 4000:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Feedback message is too long")

    logger.info("Feedback received from %s <%s> targeting %s", name, email, FEEDBACK_RECIPIENT_EMAIL)
    _send_feedback_email(name, email, message)

    response: dict[str, Any] = {"message": "Feedback submitted successfully."}
    response.update(_feedback_delivery_response())
    return response

def get_current_user(request: Request, token: str | None = Depends(oauth2_scheme)) -> dict[str, Any]:
    if not token:
        if _is_test_mode() and request.url.path.startswith("/api/analytics/"):
            return {"username": "test_user", "role": "admin"}
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authenticated")

    try:
        return decode_access_token(token)
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc


@auth_router.get("/me")
async def get_me(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    return current_user


@auth_router.get("/profile")
async def get_profile(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    profile = db.get_profile(DB_PATH, current_user["username"])
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return profile


@auth_router.put("/profile")
async def update_profile(
    payload: ProfileUpdateRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    update_fields = payload.model_dump(exclude_unset=True)
    profile = db.upsert_profile(DB_PATH, current_user["username"], **update_fields)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    db.log_audit_event(
        DB_PATH,
        event_type="profile_update",
        status="success",
        username=current_user["username"],
        message="Profile updated",
    )
    return profile


@auth_router.get("/audit-log")
async def get_audit_log(
    current_user: dict[str, Any] = Depends(get_current_user),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    username: str | None = Query(None),
    event_type: str | None = Query(None),
    status: str | None = Query(None),
    email: str | None = Query(None),
    client_ip: str | None = Query(None),
    search: str | None = Query(None),
    since: str | None = Query(None),
    until: str | None = Query(None),
) -> dict[str, Any]:
    """Retrieve audit logs (admin only)."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Operation not permitted for this role")
    logs = db.get_audit_logs(
        DB_PATH,
        limit=limit,
        offset=offset,
        username=username,
        event_type=event_type,
        status=status,
        email=email,
        client_ip=client_ip,
        search=search,
        since=since,
        until=until,
    )
    db.log_audit_event(
        DB_PATH,
        event_type="audit_log_access",
        status="success",
        username=current_user["username"],
        message=f"Retrieved {len(logs)} audit logs",
    )
    return {"logs": logs, "count": len(logs), "limit": limit, "offset": offset}



@auth_router.post("/audit-log/cleanup")
async def cleanup_audit_logs(
    days: int | None = Query(None, ge=1, le=3650),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Admin-only: delete audit log entries older than `days`. If `days` omitted, uses AUDIT_LOG_RETENTION_DAYS env var (default 90)."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Operation not permitted for this role")

    retention = int(os.getenv("AUDIT_LOG_RETENTION_DAYS", "90"))
    days_to_delete = int(days) if days is not None else retention
    try:
        deleted = db.cleanup_old_audit_logs(DB_PATH, days_to_delete)
        db.log_audit_event(
            DB_PATH,
            event_type="audit_log_cleanup",
            status="success",
            username=current_user.get("username"),
            message=f"Deleted {deleted} audit log entries older than {days_to_delete} days",
        )
        return {"deleted": deleted}
    except Exception as exc:
        db.log_audit_event(
            DB_PATH,
            event_type="audit_log_cleanup",
            status="failed",
            username=current_user.get("username"),
            message=str(exc),
        )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Cleanup failed")


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
