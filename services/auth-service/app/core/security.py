import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings
from app.core.exceptions import TokenInvalidError
from app.schemas.auth import JWTPayload


def generate_jwt(user_id: str, email: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "user_id": user_id,
        "email": email,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=settings.jwt_expiration_hours)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_jwt(token: str) -> JWTPayload:
    try:
        data = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return JWTPayload(**data)
    except jwt.ExpiredSignatureError:
        raise TokenInvalidError("Token has expired")
    except jwt.InvalidTokenError:
        raise TokenInvalidError("Invalid token")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(
        password.encode(), bcrypt.gensalt(rounds=settings.bcrypt_rounds)
    ).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def generate_recovery_token() -> str:
    return secrets.token_urlsafe(settings.recovery_token_length)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
