import hashlib

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from jose import JWTError, jwt

from app.core.config import settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    get_current_user,
    hash_password,
    verify_password,
)


def test_legacy_sha256_verification_requests_upgrade() -> None:
    legacy_hash = hashlib.sha256(b"demo:prueba2026").hexdigest()

    assert verify_password("prueba2026", legacy_hash, "demo") == (True, True)
    assert verify_password("incorrecta", legacy_hash, "demo") == (False, False)


def test_argon2_verification_does_not_request_upgrade() -> None:
    stored_hash = hash_password("contrasena-segura")

    assert verify_password("contrasena-segura", stored_hash, "demo") == (True, False)
    assert verify_password("incorrecta", stored_hash, "demo") == (False, False)


def test_access_token_round_trip_and_expiration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "jwt_secret_key", "test-only-signing-key")
    token = create_access_token({"sub": "123"})

    assert decode_access_token(token)["sub"] == "123"
    with pytest.raises(ValueError, match="mayor que cero"):
        create_access_token({"sub": "123"}, expires_minutes=0)

    expired_token = jwt.encode(
        {"sub": "123", "exp": 0},
        "test-only-signing-key",
        algorithm="HS256",
    )
    with pytest.raises(JWTError):
        decode_access_token(expired_token)


def test_invalid_access_token_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "jwt_secret_key", "test-only-signing-key")
    token = create_access_token({"sub": "123"})

    with pytest.raises(JWTError):
        decode_access_token(token + "x")


def test_bearer_dependency_protects_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "jwt_secret_key", "test-only-signing-key")
    app = FastAPI()

    @app.get("/private")
    def private(user: dict = Depends(get_current_user)) -> dict:
        return {"subject": user["sub"]}

    with TestClient(app) as client:
        assert client.get("/private").status_code == 401
        token = create_access_token({"sub": "123"})
        response = client.get(
            "/private",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    assert response.json() == {"subject": "123"}
