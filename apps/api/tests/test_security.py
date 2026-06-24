import pytest
from itsdangerous import BadSignature

from app.security import (
    create_session_token,
    decrypt_secret,
    encrypt_secret,
    hash_password,
    read_session_token,
    verify_password,
)


def test_hash_password_round_trips_and_rejects_wrong_password():
    hashed = hash_password("correct-password")
    assert hashed != "correct-password"
    assert verify_password("correct-password", hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_encrypt_secret_round_trips_and_is_not_plaintext():
    encrypted = encrypt_secret("super-secret-api-key")
    assert encrypted != "super-secret-api-key"
    assert decrypt_secret(encrypted) == "super-secret-api-key"


def test_session_token_round_trips_user_id():
    token = create_session_token("some-user-id")
    assert read_session_token(token) == "some-user-id"


def test_session_token_rejects_tampered_token():
    token = create_session_token("some-user-id")
    tampered = token[:-1] + ("a" if token[-1] != "a" else "b")
    assert read_session_token(tampered) is None


def test_session_token_rejects_garbage():
    assert read_session_token("not-a-real-token") is None
