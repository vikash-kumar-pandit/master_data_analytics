"""
Simple smoke tests for email templates and basic auth logic.
These tests do NOT require the full FastAPI app or bcrypt initialization.
"""

import sys
sys.path.insert(0, '.')

from email_templates import render_verification_email, render_password_reset_email


def test_verification_email_template():
    """Test that verification email renders correctly."""
    plain, html = render_verification_email(
        "testuser",
        "http://localhost:5173/login?verify_token=abc123",
        1440,
    )
    
    # Check plaintext
    assert "Welcome to DataSaaS Pro" in plain
    assert "verify" in plain.lower()
    assert "http://localhost:5173/login?verify_token=abc123" in plain
    assert "1440 minutes" in plain
    
    # Check HTML
    assert "DataSaaS Pro" in html  # May be wrapped in tags
    assert "http://localhost:5173/login?verify_token=abc123" in html
    assert "<a href=" in html
    assert "Verify Email" in html


def test_password_reset_email_template():
    """Test that password reset email renders correctly."""
    plain, html = render_password_reset_email(
        "testuser",
        "http://localhost:5173/login?reset_token=xyz789",
        30,
    )
    
    # Check plaintext
    assert "password reset" in plain.lower()
    assert "http://localhost:5173/login?reset_token=xyz789" in plain
    assert "30 minutes" in plain
    
    # Check HTML
    assert "password reset" in html.lower()
    assert "http://localhost:5173/login?reset_token=xyz789" in html
    assert "<a href=" in html
    assert "Reset Password" in html


def test_email_templates_have_multipart_format():
    """Verify emails return both plain and HTML."""
    plain, html = render_verification_email(
        "user",
        "http://example.com/token",
        60,
    )
    
    assert isinstance(plain, str) and len(plain) > 0
    assert isinstance(html, str) and len(html) > 0
    assert plain != html  # Should be different formats


def test_email_includes_expiry_info():
    """Verify emails include token expiry information."""
    plain, html = render_verification_email("user", "http://example.com/token", 1440)
    assert "1440" in plain or "24" in plain.lower()
    
    plain, html = render_password_reset_email("user", "http://example.com/token", 30)
    assert "30" in plain


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
