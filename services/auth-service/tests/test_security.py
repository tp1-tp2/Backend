import pytest

from app.core.exceptions import TokenInvalidError
from app.core.security import (
    decode_jwt,
    generate_jwt,
    generate_recovery_token,
    hash_password,
    hash_token,
    verify_password,
)


def test_hash_password_produces_bcrypt():
    hashed = hash_password("secret123")
    assert hashed.startswith("$2b$")


def test_verify_password_correct():
    hashed = hash_password("correct")
    assert verify_password("correct", hashed) is True


def test_verify_password_wrong():
    hashed = hash_password("correct")
    assert verify_password("wrong", hashed) is False


def test_generate_and_decode_jwt_roundtrip():
    token = generate_jwt("uid-1", "user@example.com")
    payload = decode_jwt(token)
    assert payload.user_id == "uid-1"
    assert payload.email == "user@example.com"
    assert payload.exp > payload.iat


def test_decode_invalid_jwt_raises():
    with pytest.raises(TokenInvalidError):
        decode_jwt("not.a.valid.token")


def test_decode_tampered_jwt_raises():
    token = generate_jwt("uid-1", "user@example.com")
    tampered = token[:-5] + "XXXXX"
    with pytest.raises(TokenInvalidError):
        decode_jwt(tampered)


def test_hash_token_is_64_hex_chars():
    result = hash_token("some_token_value")
    assert len(result) == 64
    assert all(c in "0123456789abcdef" for c in result)


def test_hash_token_is_deterministic():
    assert hash_token("abc") == hash_token("abc")


def test_hash_token_different_inputs_differ():
    assert hash_token("token_a") != hash_token("token_b")


def test_generate_recovery_token_min_length():
    token = generate_recovery_token()
    assert len(token) >= 32


def test_generate_recovery_token_is_unique():
    assert generate_recovery_token() != generate_recovery_token()
