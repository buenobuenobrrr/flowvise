"""Shared dependencies for FlowVise route modules.

Re-exports the things every route file needs (db handle, auth dependency,
audit logger, encryption helpers) so that `routes/*.py` modules can `from
core import db, get_current_user, ...` without circular-importing server.py.

This module deliberately does NOT define routes — only infrastructure.
"""
from server import (  # noqa: E402  (intentional late binding via server)
    db,
    logger,
    audit_log,
    get_current_user,
    encrypt_sensitive,
    decrypt_sensitive,
    validate_password_strength,
    send_verification_email,
    rate_limiter,
)

__all__ = [
    "db",
    "logger",
    "audit_log",
    "get_current_user",
    "encrypt_sensitive",
    "decrypt_sensitive",
    "validate_password_strength",
    "send_verification_email",
    "rate_limiter",
]