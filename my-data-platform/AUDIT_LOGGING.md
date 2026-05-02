# User Audit Logging Implementation

## Overview

Comprehensive audit logging system has been added to track all authentication and authorization events for compliance and security monitoring.

## Database Schema

### audit_log Table

```sql
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    username TEXT,
    email TEXT,
    client_ip TEXT,
    status TEXT NOT NULL,
    message TEXT,
    timestamp TEXT NOT NULL
)
```

**Fields:**
- `id`: Unique identifier for each audit log entry
- `event_type`: Type of event (e.g., login_attempt, register, verify_email, password_reset_request, etc.)
- `username`: Username involved in the event (nullable for certain events)
- `email`: Email address involved (nullable)
- `client_ip`: IP address of the client making the request
- `status`: Success or failure status
- `message`: Human-readable description of the event
- `timestamp`: ISO 8601 timestamp when the event occurred

## Backend Implementation

### New Functions in `db.py`

1. **`log_audit_event()`**
   - Logs an audit event to the database
   - Handles errors gracefully without failing the main operation
   - Called from all auth endpoints

2. **`get_audit_logs(limit=100, offset=0)`**
   - Retrieves audit logs, most recent first
   - Returns paginated results
   - Used by admin API endpoint

3. **`get_audit_logs_for_user(username, limit=50)`**
   - Retrieves audit logs specific to a user
   - Useful for user-specific compliance reports

### Updated Endpoints in `auth.py`

All authentication endpoints now log events:

#### POST /api/auth/login
- Logs rate limit exceeded failures
- Logs invalid credentials failures
- Logs successful login with client IP and email

#### POST /api/auth/register
- Logs rate limit exceeded failures
- Logs duplicate account failures
- Logs successful registration

#### GET /api/auth/verify-email
- Logs invalid/expired token failures
- Logs successful verification

#### POST /api/auth/resend-verification
- Logs rate limit exceeded failures
- Logs already verified scenarios
- Logs successful resend

#### POST /api/auth/password-reset/request
- Logs rate limit exceeded failures
- Logs account not found scenarios
- Logs successful reset request

#### POST /api/auth/password-reset/confirm
- Logs invalid/expired token failures
- Logs successful password reset

#### NEW: GET /api/auth/audit-log (Admin Only)
- Returns paginated audit logs
- Supports query parameters: `limit` (1-500, default 100) and `offset` (default 0)
- Requires admin role
- Logs the audit log access itself

## Frontend Implementation

### New Component: `AdminAuditLog.jsx`

Features:
- **Audit Log Table**: Displays timestamp, event type, username, email, client IP, status, and message
- **Filtering**: Filter by event type from dropdown
- **Search**: Search by username, email, or IP address
- **Pagination**: Navigate through audit logs with configurable page size (25, 50, 100, 250)
- **Status Badges**: Visual indicators for success/failed events
- **Admin Protection**: Only accessible to users with admin role

### Updated Component: `DashboardLayout.jsx`

- Added import for `AdminAuditLog` component
- Added "Audit Log" tab (AL) in sidebar for admin users
- Added conditional rendering of audit log page
- Updated page titles and subtitles to include audit log

### Updated Styles: `styles.css`

New CSS classes:
- `.audit-log-container`: Main container styling
- `.badge`: Badge styling
- `.badge-success`: Green badge for success events
- `.badge-failed`: Red badge for failed events

## Event Types Tracked

1. **login_attempt** - Failed login attempt (rate limit or invalid credentials)
2. **login_success** - Successful login
3. **register_attempt** - Failed registration attempt
4. **register** - Successful registration
5. **verify_email** - Email verification (success or failure)
6. **resend_verification** - Resend verification email request
7. **password_reset_request** - Password reset request (success or failure)
8. **password_reset_confirm** - Password reset confirmation (success or failure)
9. **audit_log_access** - Admin access to audit log endpoint

## Usage

### For Admins
1. Navigate to dashboard
2. Click "Audit Log" (AL) button in sidebar
3. View all authentication events with:
   - Timestamp (formatted in local timezone)
   - Event type and status
   - Username and email involved
   - Client IP address
   - Event message/description

### For API Integration
```bash
# Retrieve audit logs (requires admin token)
curl -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  "http://localhost:8000/api/auth/audit-log?limit=50&offset=0"

# Response
{
  "logs": [
    {
      "id": 1,
      "event_type": "login_success",
      "username": "admin",
      "email": "admin@example.com",
      "client_ip": "192.168.1.1",
      "status": "success",
      "message": "Login successful",
      "timestamp": "2024-01-15T10:30:00+00:00"
    }
  ],
  "count": 1,
  "limit": 50,
  "offset": 0
}
```

## Compliance & Security Benefits

1. **Compliance**: Complete audit trail for regulatory requirements (HIPAA, SOC 2, etc.)
2. **Security**: Track failed login attempts and rate limit violations
3. **Fraud Detection**: Monitor suspicious patterns (rapid logins, multiple failed attempts)
4. **Debugging**: Help diagnose user issues by reviewing their event history
5. **Accountability**: Track which users performed which actions and when

## Configuration

The audit logging is automatically enabled. No additional configuration is needed beyond setting up the auth system.

**Environment Variables** (optional):
- `AUDIT_LOG_RETENTION_DAYS`: Days to retain audit logs (default: 90). The application
   will remove audit entries older than this value. You can override it at runtime.
- `AUDIT_LOG_CLEANUP_INTERVAL_SECONDS`: How often the scheduled cleanup runs (seconds,
   default: 86400 = 24 hours).

## Retention & Manual Cleanup

The backend includes an automated retention task and a manual admin trigger:

- Scheduled cleanup: runs in a background daemon thread on application startup and
   deletes entries older than `AUDIT_LOG_RETENTION_DAYS` once per `AUDIT_LOG_CLEANUP_INTERVAL_SECONDS`.
- Manual trigger (admin-only): `POST /api/auth/audit-log/cleanup?days=NUMBER` will delete
   entries older than `NUMBER` days; omit `days` to use the configured retention value.

## Future Enhancements

1. **Audit Log Retention Policy**: Automatically archive/delete logs older than configured retention period
2. **Audit Log Search API**: Advanced search with date range, status filters, and text search
3. **Audit Log Export**: CSV/JSON export for compliance reporting
4. **Audit Log Alerts**: Real-time alerts for suspicious events (multiple failed logins, admin access, etc.)
5. **User Session Tracking**: Track IP address, user agent, device info for each session
6. **Rate Limit Bypass for Admins**: Allow admins to bypass rate limiting for testing/troubleshooting
7. **Database Indexes**: Add indexes on event_type, username, timestamp for faster queries
8. **Celery Integration**: Background job for audit log cleanup and archival

## Testing

### Manual Testing
1. Register a new account
2. Verify email
3. Login multiple times
4. Request password reset
5. Login as admin
6. Navigate to Audit Log tab
7. Verify all events are logged with correct timestamps and IP addresses

### API Testing
```bash
# Test audit log endpoint
curl -X GET "http://localhost:8000/api/auth/audit-log?limit=10" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"

# Verify response structure and data
```

## Files Modified

1. **Backend:**
   - `auth.py`: Added audit logging calls to all endpoints
   - `db.py`: Added audit_log table schema and functions

2. **Frontend:**
   - `AdminAuditLog.jsx`: New component for audit log viewing
   - `DashboardLayout.jsx`: Added audit log tab and routing
   - `styles.css`: Added audit log styling

## Commit Hash

`97e71df` - Add user audit logging for compliance and observability
