"""
tests/unit/test_security.py
Unit tests for JWT creation/verification and password hashing.
"""
import pytest
from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    verify_token_type, decode_token,
)


def test_password_hash_and_verify():
    plain  = "MySecret#2024"
    hashed = hash_password(plain)
    assert hashed != plain
    assert verify_password(plain, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_access_token_round_trip():
    token = create_access_token(subject=42)
    assert isinstance(token, str) and len(token) > 20
    payload = decode_token(token)
    assert payload["sub"]  == "42"
    assert payload["type"] == "access"


def test_refresh_token_round_trip():
    token = create_refresh_token(subject=99)
    subject = verify_token_type(token, expected_type="refresh")
    assert subject == "99"


def test_wrong_token_type_rejected():
    access_token = create_access_token(subject=1)
    result = verify_token_type(access_token, expected_type="refresh")
    assert result is None


def test_invalid_token_rejected():
    result = verify_token_type("not.a.valid.jwt", expected_type="access")
    assert result is None
