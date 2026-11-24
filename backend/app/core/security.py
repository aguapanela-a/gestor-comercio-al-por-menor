import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import settings

password_hasher = PasswordHasher()
bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(
    password: str,
    stored_hash: str,
    username: str,
) -> tuple[bool, bool]:
    if stored_hash.startswith("$argon2"):
        try:
            return password_hasher.verify(stored_hash, password), False
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False, False

    legacy_hash = hashlib.sha256(
        f"{username}:{password}".encode("utf-8")
    ).hexdigest()
    valid = hmac.compare_digest(legacy_hash, stored_hash)
    return valid, valid


def _jwt_secret_key() -> str:
    if not settings.jwt_secret_key:
        raise RuntimeError("JWT_SECRET_KEY no está configurada")
    return settings.jwt_secret_key


def create_access_token(
    user_data: dict[str, Any],
    expires_minutes: int | None = None,
) -> str:
    expiration = (
        settings.access_token_expire_minutes
        if expires_minutes is None
        else expires_minutes
    )
    if expiration <= 0:
        raise ValueError("La expiración del token debe ser mayor que cero")

    now = datetime.now(timezone.utc)
    payload = {
        **user_data,
        "iat": now,
        "exp": now + timedelta(minutes=expiration),
    }
    return jwt.encode(
        payload,
        _jwt_secret_key(),
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(
        token,
        _jwt_secret_key(),
        algorithms=[settings.jwt_algorithm],
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any]:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales de autenticación no válidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized

    try:
        payload = decode_access_token(credentials.credentials)
    except JWTError:
        raise unauthorized from None

    if not isinstance(payload.get("sub"), str) or not payload["sub"]:
        raise unauthorized
    return payload
