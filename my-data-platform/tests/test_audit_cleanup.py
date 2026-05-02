import sys
import pathlib
import tempfile
import sqlite3
from datetime import datetime, timedelta, timezone

# Ensure backend module path is importable
backend_dir = pathlib.Path(__file__).resolve().parents[1] / "my-data-platform" / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import db


def test_cleanup_old_audit_logs():
    # Create a temporary sqlite file
    fd, tmp_path = tempfile.mkstemp(suffix=".sqlite3")
    try:
        tmp_path = tmp_path
        # Initialize DB schema
        db.init_db(tmp_path)

        conn = sqlite3.connect(tmp_path)
        cur = conn.cursor()

        now = datetime.now(timezone.utc)
        old_ts = (now - timedelta(days=100)).isoformat()
        recent_ts = (now - timedelta(days=10)).isoformat()

        # Insert two audit rows: one old, one recent
        cur.execute(
            "INSERT INTO audit_log (event_type, username, email, client_ip, status, message, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("test_event", "user1", "u1@example.com", "127.0.0.1", "success", "old event", old_ts),
        )
        cur.execute(
            "INSERT INTO audit_log (event_type, username, email, client_ip, status, message, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("test_event", "user2", "u2@example.com", "127.0.0.2", "success", "recent event", recent_ts),
        )
        conn.commit()
        conn.close()

        # Run cleanup for 90 days -- should remove the old event only
        deleted = db.cleanup_old_audit_logs(tmp_path, days=90)
        assert deleted == 1, f"expected 1 deleted row, got {deleted}"

        # Verify remaining rows
        conn = sqlite3.connect(tmp_path)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM audit_log")
        remaining = cur.fetchone()[0]
        conn.close()
        assert remaining == 1, f"expected 1 remaining row, got {remaining}"
    finally:
        try:
            import os

            os.close(fd)
            os.remove(tmp_path)
        except Exception:
            pass
