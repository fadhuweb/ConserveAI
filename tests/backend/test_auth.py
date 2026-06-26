"""Unit tests for the authentication building blocks: password hashing,
the password policy, and JWT access / reset tokens. No database required.
"""
from src.backend.auth.password import hash_password, verify_password, password_problems
from src.backend.auth.jwt_handler import (
    create_access_token, decode_token, create_reset_token, decode_reset_token,
)

STRONG = "Str0ng!pass"   # 8+ chars, upper, lower, digit, special


def test_password_hash_is_not_plaintext():
    h = hash_password(STRONG)
    assert h != STRONG
    assert h.startswith("$2")          # bcrypt hash prefix


def test_password_verify_roundtrip():
    h = hash_password(STRONG)
    assert verify_password(STRONG, h) is True
    assert verify_password("wrong-password", h) is False


def test_password_policy_accepts_strong_password():
    assert password_problems(STRONG) == []


def test_password_policy_flags_each_weakness():
    assert "at least 8 characters" in password_problems("Aa1!")     # too short
    assert "a number" in password_problems("NoNumber!")             # missing digit
    assert "a special character" in password_problems("NoSpecial1") # missing symbol


def test_access_token_roundtrip():
    token = create_access_token({"sub": "admin", "role": "admin", "park_id": None})
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "admin"
    assert payload["role"] == "admin"


def test_invalid_token_returns_none():
    assert decode_token("clearly.not.a.jwt") is None


def test_reset_token_roundtrip():
    token = create_reset_token("manager_yankari")
    assert decode_reset_token(token) == "manager_yankari"


def test_access_token_is_not_accepted_as_reset_token():
    # An ordinary access token lacks purpose="reset" and must be rejected.
    token = create_access_token({"sub": "manager_yankari", "role": "manager", "park_id": "yankari"})
    assert decode_reset_token(token) is None
