# DataSaaS Backend

FastAPI-based backend for DataSaaS Pro with enterprise authentication features.

## Features

- **JWT-based Authentication**: Secure token-based login with configurable expiry
- **Email Verification**: Users must verify their email before login
- **Password Reset Flow**: Secure password reset with time-limited tokens
- **Rate Limiting**: Protects against brute force attacks (configurable limits per IP + username)
- **Database-Backed Storage**: SQLite for users, tokens, and audit logs
- **SMTP Integration**: Multipart HTML/plaintext email sending
- **Role-Based Access Control (RBAC)**: Built-in support for admin, analyst, and viewer roles

## Quick Start

### 1. Install Dependencies

```bash
cd my-data-platform/backend
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.env.sample` to `.env` and update values:

```bash
cp .env.sample .env
```

Key settings:
- `JWT_SECRET_KEY`: Set to a strong random string (min 32 chars)
- `APP_BASE_URL`: Frontend URL for email links (default: `http://localhost:5173`)
- `AUTH_DB_PATH`: SQLite database location (default: `./auth.sqlite3`)
- SMTP settings (optional, leave empty for console logging)

### 3. Run the Backend

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`.

## Database

The backend automatically initializes SQLite tables on startup:

- **users**: User accounts with hashed passwords, roles, and verification status
- **tokens**: Email verification and password reset tokens with expiry

Demo users are seeded on first run (see `auth.py` for credentials).

## Email Configuration

### Development (Console Logging)

Leave `SMTP_HOST` empty in `.env`. Emails will be logged to the console:

```
INFO auth: Email provider not configured. Simulated email to user@example.com subject=Verify your DataSaaS account
INFO auth: Email plain: Hello user, ...
INFO auth: Email html: <html><body>...
```

### Production (Real SMTP)

Configure SMTP provider (e.g., Gmail, SendGrid, AWS SES):

```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=noreply@datasaas.local
```

**Gmail Setup** (if using Gmail):
1. Enable [2-Step Verification](https://support.google.com/accounts/answer/185839)
2. Generate an [App Password](https://support.google.com/accounts/answer/185833)
3. Use the app password in `SMTP_PASSWORD`

### Email Templates

HTML and plaintext email templates are in `email_templates.py`. Customize them as needed for branding.

## API Endpoints

### Authentication

- `POST /api/auth/login` — Login with username & password
- `POST /api/auth/register` — Register new account (requires email)
- `GET /api/auth/verify-email` — Verify email with token
- `POST /api/auth/resend-verification` — Resend verification email
- `POST /api/auth/password-reset/request` — Request password reset
- `POST /api/auth/password-reset/confirm` — Confirm password reset with token
- `GET /api/auth/me` — Get current user info (requires token)

## Security Notes

- Passwords are hashed using bcrypt (configured in `passlib`)
- Tokens are hashed with SHA-256 before storage
- One-time tokens expire after configured duration (default: 30 min for reset, 24 hours for verify)
- Rate limiting prevents brute force (5 attempts per 15 min for login, configurable)
- Always use HTTPS in production
- Use strong `JWT_SECRET_KEY` (30+ random chars)

## Development & Testing

### Local Testing with Demo Users

Demo users are auto-seeded (see `auth.py`):

- **admin_user** / **password123** (admin role)
- **data_analyst** / **password123** (analyst role)
- **guest_viewer** / **password123** (viewer role)

All demo accounts are pre-verified and ready to use.

### Password Requirements

- Min 8 characters
- Max 128 characters
- At least 1 uppercase letter
- At least 1 lowercase letter
- At least 1 digit
- At least 1 special character

### Debugging

Set `LOG_LEVEL=DEBUG` in `.env` for verbose logging.

## Dependencies

See `requirements.txt` for full list. Key packages:

- `fastapi` — Web framework
- `uvicorn` — ASGI server
- `pydantic` — Data validation
- `passlib[bcrypt]` — Password hashing
- `pyjwt` — JWT token handling
- `python-multipart` — Form parsing

## Production Deployment

1. Set `APP_ENV=production` in `.env`
2. Generate a strong `JWT_SECRET_KEY` (use `openssl rand -hex 32`)
3. Configure real SMTP provider
4. Use persistent database (move `.sqlite3` to stable storage or migrate to PostgreSQL)
5. Deploy behind a reverse proxy (nginx, Traefik) with HTTPS/SSL
6. Set secure headers and CORS policies
7. Monitor logs and set up alerting

## Troubleshooting

**Issue**: "Email provider not configured"
- **Fix**: Set `SMTP_HOST` in `.env` for real sending, or ignore for dev logging

**Issue**: Login fails with "Email is not verified"
- **Fix**: Verify email via token link, or seed verified demo users

**Issue**: Token expired errors
- **Fix**: Increase `JWT_EXPIRE_HOURS` in `.env`, or refresh tokens on frontend

## License

Same as parent project.
