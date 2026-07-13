import pytest
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
from share_manager import (
    create_share_link, get_share, increment_view_count,
    record_download, list_my_shares, revoke_share, _load_shares
)
import share_manager

@pytest.fixture(autouse=True)
def setup_temp_shares_path(tmp_path, monkeypatch):
    # Set a temp directory and temp shares file for each test
    temp_file = tmp_path / "shares.json"
    monkeypatch.setattr(share_manager, "SHARES_PATH", temp_file)
    yield temp_file
    if temp_file.exists():
        temp_file.unlink()

def test_load_shares_invalid_json(setup_temp_shares_path):
    temp_file = setup_temp_shares_path
    temp_file.write_text("invalid-json", encoding="utf-8")
    assert _load_shares() == []

def test_load_shares_nonexistent():
    # If the file doesn't exist, should return empty list
    assert _load_shares() == []

def test_create_share_link_validation():
    # report_title cannot be empty
    with pytest.raises(ValueError, match="report_title cannot be empty"):
        create_share_link(report_title="", report_data={"data": 1})
    
    # report_data must be a dict
    with pytest.raises(ValueError, match="report_data must be a dictionary"):
        create_share_link(report_title="Title", report_data="not a dict")
        
    # expires_days check
    with pytest.raises(ValueError, match="expires_days must be between 1 and 365"):
        create_share_link(report_title="Title", report_data={}, expires_days=0)
    with pytest.raises(ValueError, match="expires_days must be between 1 and 365"):
        create_share_link(report_title="Title", report_data={}, expires_days=366)
        
    # access_level check
    with pytest.raises(ValueError, match="access_level must be 'view', 'download', or 'edit'"):
        create_share_link(report_title="Title", report_data={}, access_level="invalid")

def test_create_share_link_success():
    res = create_share_link(
        report_title="My Report",
        report_data={"key": "val"},
        created_by={"username": "user123"},
        expires_days=10,
        access_level="download"
    )
    assert "token" in res
    assert res["share_url"] == f"/share/{res['token']}"
    assert res["access_level"] == "download"
    
    # Retrieve and check
    share = get_share(res["token"])
    assert share is not None
    assert share["report_title"] == "My Report"
    assert share["report_data"] == {"key": "val"}
    assert share["created_by"] == "user123"
    assert share["access_level"] == "download"
    assert share["view_count"] == 0

def test_get_share_validation():
    with pytest.raises(ValueError, match="token cannot be empty"):
        get_share("")

def test_get_share_expired(setup_temp_shares_path):
    temp_file = setup_temp_shares_path
    expired_time = datetime.now(timezone.utc) - timedelta(days=1)
    shares = [{
        "token": "expired-token",
        "report_title": "Expired",
        "report_data": {},
        "expires_at": expired_time.isoformat(),
    }]
    temp_file.write_text(json.dumps(shares), encoding="utf-8")
    assert get_share("expired-token") is None

def test_get_share_invalid_expiry(setup_temp_shares_path):
    temp_file = setup_temp_shares_path
    shares = [{
        "token": "invalid-expiry-token",
        "report_title": "Invalid Expiry",
        "report_data": {},
        "expires_at": "not-a-date",
    }]
    temp_file.write_text(json.dumps(shares), encoding="utf-8")
    assert get_share("invalid-expiry-token") is None

def test_get_share_not_found():
    assert get_share("nonexistent-token") is None

def test_increment_view_count():
    with pytest.raises(ValueError, match="token cannot be empty"):
        increment_view_count("")
        
    res = create_share_link(report_title="Report", report_data={})
    token = res["token"]
    
    increment_view_count(token)
    assert get_share(token)["view_count"] == 1
    
    increment_view_count(token)
    assert get_share(token)["view_count"] == 2
    
    # Increment nonexistent does nothing and doesn't raise error
    increment_view_count("nonexistent")

def test_record_download():
    with pytest.raises(ValueError, match="token cannot be empty"):
        record_download("", "pdf")
    with pytest.raises(ValueError, match="format cannot be empty"):
        record_download("token", "")
    with pytest.raises(ValueError, match="Invalid format"):
        record_download("token", "invalid")
        
    res = create_share_link(report_title="Report", report_data={})
    token = res["token"]
    
    record_download(token, "pdf", "downloader_user")
    share = get_share(token)
    assert len(share["downloads"]) == 1
    assert share["downloads"][0]["format"] == "pdf"
    assert share["downloads"][0]["username"] == "downloader_user"
    
    # Anonymous download
    record_download(token, "csv")
    share = get_share(token)
    assert len(share["downloads"]) == 2
    assert share["downloads"][1]["username"] == "anonymous"

def test_list_my_shares():
    with pytest.raises(ValueError, match="username cannot be empty"):
        list_my_shares("")
    with pytest.raises(ValueError, match="limit must be between 1 and 100"):
        list_my_shares("user", limit=0)
    with pytest.raises(ValueError, match="limit must be between 1 and 100"):
        list_my_shares("user", limit=101)
        
    create_share_link(report_title="R1", report_data={}, created_by={"username": "alice"})
    create_share_link(report_title="R2", report_data={}, created_by={"username": "alice"})
    create_share_link(report_title="R3", report_data={}, created_by={"username": "bob"})
    
    alice_shares = list_my_shares("alice")
    assert len(alice_shares) == 2
    assert alice_shares[0]["report_title"] == "R2" # Reversed order (most recent first)
    assert alice_shares[1]["report_title"] == "R1"
    
    bob_shares = list_my_shares("bob")
    assert len(bob_shares) == 1
    assert bob_shares[0]["report_title"] == "R3"

def test_revoke_share():
    with pytest.raises(ValueError, match="token cannot be empty"):
        revoke_share("")
        
    res = create_share_link(report_title="R", report_data={}, created_by={"username": "alice"})
    token = res["token"]
    
    # Revoke with wrong user
    assert revoke_share(token, username="bob") is False
    assert get_share(token) is not None
    
    # Revoke with correct user
    assert revoke_share(token, username="alice") is True
    assert get_share(token) is None
    
    # Revoke again
    assert revoke_share(token) is False
    
    # Create another one and revoke with anonymous/no username
    res2 = create_share_link(report_title="R2", report_data={}, created_by={"username": "alice"})
    token2 = res2["token"]
    assert revoke_share(token2) is True
    assert get_share(token2) is None
