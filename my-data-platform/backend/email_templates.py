from __future__ import annotations

from typing import Tuple


def render_verification_email(username: str, verify_link: str, minutes: int) -> Tuple[str, str]:
    plain = (
        f"Hello {username},\n\n"
        "Welcome to DataSaaS Pro. Please verify your email by visiting the link below:\n\n"
        f"{verify_link}\n\n"
        f"This link expires in {minutes} minutes.\n\n"
        "If you did not create an account, you can safely ignore this message.\n"
    )

    html = (
        "<html><body>"
        f"<p>Hello <strong>{username}</strong>,</p>"
        "<p>Welcome to <em>DataSaaS Pro</em>. Please verify your email by clicking the button below:</p>"
        f"<p><a href=\"{verify_link}\" style=\"display:inline-block;padding:10px 14px;background:#1a73e8;color:#fff;border-radius:6px;text-decoration:none;\">Verify Email</a></p>"
        f"<p style=\"color:#666;\">This link expires in {minutes} minutes.</p>"
        "<hr/><p style=\"font-size:12px;color:#888;\">If you did not create an account, you can ignore this message.</p>"
        "</body></html>"
    )

    return plain, html


def render_password_reset_email(username: str, reset_link: str, minutes: int) -> Tuple[str, str]:
    plain = (
        f"Hello {username},\n\n"
        "A password reset was requested for your account. Use the link below to reset your password:\n\n"
        f"{reset_link}\n\n"
        f"This link expires in {minutes} minutes.\n\n"
        "If you did not request a password reset, please contact support or ignore this message.\n"
    )

    html = (
        "<html><body>"
        f"<p>Hello <strong>{username}</strong>,</p>"
        "<p>A password reset was requested for your account. Click below to reset your password:</p>"
        f"<p><a href=\"{reset_link}\" style=\"display:inline-block;padding:10px 14px;background:#d9534f;color:#fff;border-radius:6px;text-decoration:none;\">Reset Password</a></p>"
        f"<p style=\"color:#666;\">This link expires in {minutes} minutes.</p>"
        "<hr/><p style=\"font-size:12px;color:#888;\">If you did not request this, you can ignore this message.</p>"
        "</body></html>"
    )

    return plain, html
