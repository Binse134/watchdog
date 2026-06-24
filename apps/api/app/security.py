import bcrypt
from cryptography.fernet import Fernet
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.config import settings

_fernet = Fernet(settings.encryption_key.encode())
_serializer = URLSafeTimedSerializer(settings.session_secret, salt="watchdog-session")
_reset_serializer = URLSafeTimedSerializer(settings.session_secret, salt="watchdog-password-reset")

SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 14  # 14 days
RESET_TOKEN_MAX_AGE_SECONDS = 60 * 60  # 1 hour


def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), password_hash.encode())


def encrypt_secret(plain_text: str) -> str:
    return _fernet.encrypt(plain_text.encode()).decode()


def decrypt_secret(encrypted_text: str) -> str:
    return _fernet.decrypt(encrypted_text.encode()).decode()


def create_session_token(user_id: str) -> str:
    return _serializer.dumps({"user_id": user_id})


def read_session_token(token: str) -> str | None:
    try:
        data = _serializer.loads(token, max_age=SESSION_MAX_AGE_SECONDS)
        return data.get("user_id")
    except (BadSignature, SignatureExpired):
        return None


def create_reset_token(user_id: str) -> str:
    return _reset_serializer.dumps({"user_id": user_id})


def read_reset_token(token: str) -> str | None:
    try:
        data = _reset_serializer.loads(token, max_age=RESET_TOKEN_MAX_AGE_SECONDS)
        return data.get("user_id")
    except (BadSignature, SignatureExpired):
        return None
