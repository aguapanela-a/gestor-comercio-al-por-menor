import hashlib

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import create_access_token, verify_password
from app.services.identidad.dependencies import get_identity_db
from app.services.identidad.main import app


class FakeResult:
    def __init__(self, value) -> None:
        self.value = value

    def mappings(self) -> "FakeResult":
        return self

    def first(self):
        return self.value


class FakeDatabaseSession:
    def __init__(self, user=None) -> None:
        self.user = user
        self.statements: list[tuple[str, dict | None]] = []
        self.commits = 0

    def execute(self, statement, parameters=None) -> FakeResult:
        self.statements.append((str(statement), parameters))
        return FakeResult(self.user)

    def commit(self) -> None:
        self.commits += 1


def test_login_rejects_unknown_user_without_database_connection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = FakeDatabaseSession()
    monkeypatch.setitem(
        app.dependency_overrides,
        get_identity_db,
        lambda: db,
    )
    with TestClient(app) as client:
        response = client.post(
            "/auth/login",
            json={"nombre_usuario": "inexistente", "password": "no-importa"},
        )

    assert response.status_code == 401
    assert db.commits == 0


def test_invalid_legacy_password_does_not_migrate_hash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    legacy_hash = hashlib.sha256(b"demo:prueba2026").hexdigest()
    db = FakeDatabaseSession(
        {
            "id_usuario": 1,
            "id_empleado": 2,
            "nombre_usuario": "demo",
            "password_hash": legacy_hash,
            "estado_usuario": "activo",
            "estado_empleado": "activo",
            "nombre_completo": "Usuario de prueba",
            "cargo": "Prueba",
            "id_sede": 1,
        }
    )
    monkeypatch.setitem(
        app.dependency_overrides,
        get_identity_db,
        lambda: db,
    )

    with TestClient(app) as client:
        response = client.post(
            "/auth/login",
            json={"nombre_usuario": "demo", "password": "incorrecta"},
        )

    assert response.status_code == 401
    assert not any("UPDATE identidad.usuarios" in query for query, _ in db.statements)
    assert db.commits == 0


def test_login_migrates_legacy_hash_after_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "jwt_secret_key", "test-only-signing-key")
    legacy_hash = hashlib.sha256(b"demo:prueba2026").hexdigest()
    db = FakeDatabaseSession(
        {
            "id_usuario": 1,
            "id_empleado": 2,
            "nombre_usuario": "demo",
            "password_hash": legacy_hash,
            "estado_usuario": "activo",
            "estado_empleado": "activo",
            "nombre_completo": "Usuario de prueba",
            "cargo": "Prueba",
            "id_sede": 1,
        }
    )
    monkeypatch.setitem(
        app.dependency_overrides,
        get_identity_db,
        lambda: db,
    )

    with TestClient(app) as client:
        response = client.post(
            "/auth/login",
            json={"nombre_usuario": "demo", "password": "prueba2026"},
        )

    assert response.status_code == 200
    assert "password_hash" not in response.json()
    assert "password" not in response.json()
    update = next(
        entry for entry in db.statements if "UPDATE identidad.usuarios" in entry[0]
    )
    assert update[1]["password_hash"].startswith("$argon2")
    assert db.commits == 1
    assert verify_password("prueba2026", update[1]["password_hash"], "demo") == (
        True,
        False,
    )


def test_identity_health(assert_health_endpoints) -> None:
    assert_health_endpoints(app, "identidad")


def test_current_user_returns_only_profile_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "jwt_secret_key", "identity-test-signing-key")
    db = FakeDatabaseSession(
        {
            "id_usuario": 1,
            "id_empleado": 2,
            "nombre_usuario": "demo",
            "estado_usuario": "activo",
            "nombre_completo": "Usuario de prueba",
            "cargo": "Prueba",
            "id_sede": 1,
            "correo": None,
            "estado_empleado": "activo",
        }
    )
    monkeypatch.setitem(app.dependency_overrides, get_identity_db, lambda: db)
    token = create_access_token({"sub": "1"})

    with TestClient(app) as client:
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    assert response.json()["nombre_usuario"] == "demo"
    assert "password_hash" not in response.json()
    assert "estado_usuario" not in response.json()
