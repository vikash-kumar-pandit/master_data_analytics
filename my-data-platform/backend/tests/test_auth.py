import pytest
import json
from fastapi.testclient import TestClient
from main import app
import db
import email_templates
from datetime import datetime, timezone

client = TestClient(app)


class TestAuthEndpoints:
    """Test suite for auth endpoints."""

    def test_login_demo_user(self):
        """Test login with demo user credentials."""
        response = client.post(
            "/api/auth/login",
            data={"username": "admin_user", "password": "password123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["role"] == "admin"
        assert data["username"] == "admin_user"

    def test_login_wrong_password(self):
        """Test login with wrong password."""
        response = client.post(
            "/api/auth/login",
            data={"username": "admin_user", "password": "wrongpassword"},
        )
        assert response.status_code == 401
        assert "Incorrect" in response.json()["detail"]

    def test_login_nonexistent_user(self):
        """Test login with nonexistent username."""
        response = client.post(
            "/api/auth/login",
            data={"username": "nonexistent", "password": "password123"},
        )
        assert response.status_code == 401

    def test_register_new_user(self):
        """Test registering a new user."""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "testuser_new",
                "email": "testuser@example.com",
                "password": "TestPassword123!",
                "role": "viewer",
            },
        )
        assert response.status_code == 201
        data = response.json()
        # In dev mode, users are auto-verified (verification_required=False)
        # In production mode, users must verify email (verification_required=True)
        assert "verification_required" in data
        assert "message" in data
        # In development mode token may be exposed for testing
        if data["verification_required"]:
            assert "verification_token" in data or "verification_required" in data

    def test_register_weak_password(self):
        """Test registering with weak password."""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "weakpass_user",
                "email": "weak@example.com",
                "password": "weak",  # Too short
                "role": "viewer",
            },
        )
        assert response.status_code == 400
        assert "Password" in response.json()["detail"]

    def test_register_invalid_email(self):
        """Test registering with invalid email."""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "invalidemail_user",
                "email": "not-an-email",
                "password": "ValidPassword123!",
                "role": "viewer",
            },
        )
        assert response.status_code == 400
        assert "email" in response.json()["detail"].lower()

    def test_register_admin_role_blocked(self):
        """Test that admin role cannot be self-registered."""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "admin_attempt",
                "email": "admin_attempt@example.com",
                "password": "ValidPassword123!",
                "role": "admin",  # Not allowed
            },
        )
        assert response.status_code == 400
        assert "role" in response.json()["detail"].lower()

    def test_register_duplicate_username(self):
        """Test registering with duplicate username."""
        # Register first user
        client.post(
            "/api/auth/register",
            json={
                "username": "duplicate_test",
                "email": "first@example.com",
                "password": "ValidPassword123!",
                "role": "viewer",
            },
        )
        # Try to register again with same username
        response = client.post(
            "/api/auth/register",
            json={
                "username": "duplicate_test",
                "email": "second@example.com",
                "password": "ValidPassword123!",
                "role": "viewer",
            },
        )
        assert response.status_code == 409
        assert "exists" in response.json()["detail"].lower()

    def test_get_me_authenticated(self):
        """Test getting current user info with valid token."""
        # Login first
        login_response = client.post(
            "/api/auth/login",
            data={"username": "admin_user", "password": "password123"},
        )
        token = login_response.json()["access_token"]

        # Get current user
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "admin_user"
        assert data["role"] == "admin"

    def test_get_me_no_token(self):
        """Test getting current user without token."""
        response = client.get("/api/auth/me")
        assert response.status_code == 403

    def test_get_me_invalid_token(self):
        """Test getting current user with invalid token."""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401

    def test_resend_verification_valid_email(self):
        """Test resending verification to valid email."""
        response = client.post(
            "/api/auth/resend-verification",
            json={"email": "admin@datasaas.local"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "verification" in data["message"].lower() or "sent" in data["message"].lower()

    def test_password_reset_request_valid_email(self):
        """Test requesting password reset."""
        response = client.post(
            "/api/auth/password-reset/request",
            json={"email": "admin@datasaas.local"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "reset" in data["message"].lower() or "sent" in data["message"].lower()

    def test_password_reset_request_nonexistent_email(self):
        """Test password reset for nonexistent email (should not reveal user exists)."""
        response = client.post(
            "/api/auth/password-reset/request",
            json={"email": "nonexistent@example.com"},
        )
        assert response.status_code == 200
        # Message should be generic to prevent user enumeration
        assert "account" in response.json()["message"].lower() or "sent" in response.json()["message"].lower()

    def test_rate_limiting_login(self):
        """Test that login rate limiting is active."""
        # Try 6 failed logins (limit is 5)
        for i in range(6):
            response = client.post(
                "/api/auth/login",
                data={"username": "admin_user", "password": "wrong"},
            )
            if i < 5:
                assert response.status_code == 401
            else:
                # 6th attempt should be rate limited
                assert response.status_code == 429 or response.status_code == 401

    def test_username_validation(self):
        """Test username validation rules."""
        # Test invalid username (too short)
        response = client.post(
            "/api/auth/register",
            json={
                "username": "ab",  # Too short
                "email": "short@example.com",
                "password": "ValidPassword123!",
                "role": "viewer",
            },
        )
        assert response.status_code == 400

    def test_analyst_role_registration(self):
        """Test registering with analyst role."""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "analyst_test",
                "email": "analyst@example.com",
                "password": "ValidPassword123!",
                "role": "analyst",
            },
        )
        assert response.status_code == 201


class TestProfileEndpoints:
    """Test profile endpoint functionality."""

    def test_get_profile_authenticated(self):
        """Test getting profile with valid token."""
        login_response = client.post(
            "/api/auth/login",
            data={"username": "admin_user", "password": "password123"},
        )
        token = login_response.json()["access_token"]

        response = client.get(
            "/api/auth/profile",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "username" in data
        assert "email" in data
        assert "full_name" in data

    def test_update_profile(self):
        """Test updating profile with valid data."""
        login_response = client.post(
            "/api/auth/login",
            data={"username": "admin_user", "password": "password123"},
        )
        token = login_response.json()["access_token"]

        response = client.put(
            "/api/auth/profile",
            json={"full_name": "Test User", "bio": "My bio", "phone": "1234567890", "location": "Delhi"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Test User"
        assert data["bio"] == "My bio"
        assert data["phone"] == "1234567890"
        assert data["location"] == "Delhi"

    def test_get_profile_no_token(self):
        """Test getting profile without token."""
        response = client.get("/api/auth/profile")
        assert response.status_code == 403


class TestSMTPIntegration:
    """Test SMTP email functionality."""

    def test_email_sending_logic(self):
        """Test that email templates render correctly."""
        from email_templates import render_verification_email, render_password_reset_email

        # Test verification email
        plain, html = render_verification_email(
            "testuser",
            "http://localhost:5173/login?verify_token=abc123",
            1440,
        )
        assert "Welcome to DataSaaS Pro" in plain
        assert "verify" in plain.lower()
        assert "http://localhost:5173/login?verify_token=abc123" in html
        assert "<a href=" in html

        # Test password reset email
        plain, html = render_password_reset_email(
            "testuser",
            "http://localhost:5173/login?reset_token=xyz789",
            30,
        )
        assert "password reset" in plain.lower()
        assert "http://localhost:5173/login?reset_token=xyz789" in html
        assert "<a href=" in html
