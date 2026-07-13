import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
TEST_DB_PATH = ""
from database import SessionLocal
from models import User, Profile, Token, AuditLog
import db as db_module

@pytest.fixture(autouse=True)
def clean_db_tables():
    with SessionLocal() as session:
        session.query(Token).delete()
        session.query(AuditLog).delete()
        session.query(Profile).delete()
        session.query(User).filter(User.username.notin_(["admin_user", "data_analyst", "guest_viewer"])).delete()
        session.commit()
    yield

def test_init_db():
    # Calling init_db should execute without crashing
    db_module.init_db(TEST_DB_PATH)

def test_user_operations():
    username = "new_test_user"
    email = "new_test@example.com"
    pwd_hash = "hashed_pw"
    role = "analyst"
    
    # create_user
    db_module.create_user(TEST_DB_PATH, username, pwd_hash, role, email, False, datetime.now(timezone.utc))
    
    # get_user
    u = db_module.get_user(TEST_DB_PATH, username)
    assert u is not None
    assert u["username"] == username
    assert u["email"] == email
    assert u["role"] == role
    assert u["verified"] is False
    
    # get_user nonexistent
    assert db_module.get_user(TEST_DB_PATH, "nonexistent") is None
    
    # get_user_by_email
    assert db_module.get_user_by_email(TEST_DB_PATH, email) == username
    assert db_module.get_user_by_email(TEST_DB_PATH, "missing@example.com") is None
    
    # get_user_by_username_or_email
    assert db_module.get_user_by_username_or_email(TEST_DB_PATH, username)["username"] == username
    assert db_module.get_user_by_username_or_email(TEST_DB_PATH, email)["username"] == username
    assert db_module.get_user_by_username_or_email(TEST_DB_PATH, "nonexistent") is None
    
    # update_user_verified
    db_module.update_user_verified(TEST_DB_PATH, username, True)
    assert db_module.get_user(TEST_DB_PATH, username)["verified"] is True
    
    # update_user_password
    db_module.update_user_password(TEST_DB_PATH, username, "new_hashed_pw")
    assert db_module.get_user(TEST_DB_PATH, username)["password_hash"] == "new_hashed_pw"


def test_token_operations():
    payload = {"username": "token_user", "email": "token@example.com"}
    
    # mint_token
    raw_token = db_module.mint_token(TEST_DB_PATH, payload, expires_minutes=15, token_type="reset")
    assert raw_token is not None
    
    # consume_token success
    retrieved_payload = db_module.consume_token(TEST_DB_PATH, raw_token, token_type="reset")
    assert retrieved_payload == payload
    
    # consume_token nonexistent
    with pytest.raises(KeyError, match="token not found"):
        db_module.consume_token(TEST_DB_PATH, "invalid_token", "reset")
        
    # consume_token type mismatch
    raw_token2 = db_module.mint_token(TEST_DB_PATH, payload, expires_minutes=15, token_type="reset")
    with pytest.raises(KeyError, match="token type mismatch"):
        db_module.consume_token(TEST_DB_PATH, raw_token2, "verify")
        
    # consume_token expired
    raw_token3 = db_module.mint_token(TEST_DB_PATH, payload, expires_minutes=-5, token_type="reset")
    with pytest.raises(KeyError, match="token expired"):
        db_module.consume_token(TEST_DB_PATH, raw_token3, "reset")


def test_audit_logs():
    # log_audit_event
    db_module.log_audit_event(
        TEST_DB_PATH, event_type="login", status="success",
        username="user1", email="user1@example.com", client_ip="127.0.0.1", message="Logged in"
    )
    db_module.log_audit_event(
        TEST_DB_PATH, event_type="export", status="failed",
        username="user2", email="user2@example.com", client_ip="192.168.1.1", message="Export failed"
    )
    
    # get_audit_logs_for_user
    user1_logs = db_module.get_audit_logs_for_user(TEST_DB_PATH, "user1")
    assert len(user1_logs) == 1
    assert user1_logs[0]["event_type"] == "login"
    assert user1_logs[0]["status"] == "success"
    
    # get_audit_logs filters
    assert len(db_module.get_audit_logs(TEST_DB_PATH, event_type="export")) == 1
    assert len(db_module.get_audit_logs(TEST_DB_PATH, status="failed")) == 1
    assert len(db_module.get_audit_logs(TEST_DB_PATH, email="user1@example.com")) == 1
    assert len(db_module.get_audit_logs(TEST_DB_PATH, client_ip="192.168.1.1")) == 1
    
    # Search
    assert len(db_module.get_audit_logs(TEST_DB_PATH, search="failed")) == 1
    
    # since / until
    now = datetime.now(timezone.utc)
    since = now - timedelta(minutes=5)
    until = now + timedelta(minutes=5)
    assert len(db_module.get_audit_logs(TEST_DB_PATH, since=since, until=until)) == 2
    
    # log_audit_event exception handling
    # Passing an object that can't be logged to force database error/rollback
    with patch("database.SessionLocal") as mock_session_class:
        mock_db = mock_session_class.return_value.__enter__.return_value
        mock_db.add.side_effect = Exception("DB error")
        
        # Should not raise exception because it's caught and logged to logger
        db_module.log_audit_event(TEST_DB_PATH, "test", "status")


def test_cleanup_audit_logs():
    # Zero/negative days returns 0
    assert db_module.cleanup_old_audit_logs(TEST_DB_PATH, days=0) == 0
    
    # Log events with past and current timestamps
    with SessionLocal() as session:
        log_old = AuditLog(
            event_type="test", status="success",
            timestamp=datetime.now(timezone.utc) - timedelta(days=10)
        )
        log_new = AuditLog(
            event_type="test", status="success",
            timestamp=datetime.now(timezone.utc)
        )
        session.add_all([log_old, log_new])
        session.commit()
        
    deleted = db_module.cleanup_old_audit_logs(TEST_DB_PATH, days=5)
    assert deleted == 1


def test_profile_operations():
    username = "profile_user"
    db_module.create_user(TEST_DB_PATH, username, "pw", "analyst", "profile@example.com", True, datetime.now(timezone.utc))
    
    # get_profile without existing Profile record
    p = db_module.get_profile(TEST_DB_PATH, username)
    assert p is not None
    assert p["username"] == username
    assert p["full_name"] == ""
    
    # get_profile of nonexistent user
    assert db_module.get_profile(TEST_DB_PATH, "nonexistent") is None
    
    # upsert_profile (insert)
    p_updated = db_module.upsert_profile(
        TEST_DB_PATH, username, full_name="Alice Smith", bio="Data Analyst", preferences={"theme": "dark"}
    )
    assert p_updated["full_name"] == "Alice Smith"
    assert p_updated["bio"] == "Data Analyst"
    assert p_updated["preferences"] == {"theme": "dark"}
    
    # upsert_profile (update)
    p_updated2 = db_module.upsert_profile(TEST_DB_PATH, username, full_name="Alice Jones", bio=None)
    assert p_updated2["full_name"] == "Alice Jones"
    assert p_updated2["bio"] == "Data Analyst" # kept old bio because None was passed and allowed_fields is filtered
    
    # upsert_profile nonexistent user
    assert db_module.upsert_profile(TEST_DB_PATH, "nonexistent", full_name="test") is None
