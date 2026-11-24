import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.services.identidad.dependencies import get_identity_db
from app.services.identidad.main import app


class FakeResult:
    def __init__(self, row=None, rows=None, rowcount=0) -> None:
        self.row = row
        self.rows = rows if rows is not None else ([row] if row is not None else [])
        self.rowcount = rowcount

    def mappings(self):
        return self

    def all(self):
        return self.rows

    def first(self):
        return self.rows[0] if self.rows else None

    def one(self):
        return self.rows[0]


class FakeDatabaseSession:
    def __init__(self, *results: FakeResult) -> None:
        self.results = list(results)
        self.statements: list[tuple[str, dict | None]] = []
        self.commits = 0
        self.rollbacks = 0

    def execute(self, statement, parameters=None):
        self.statements.append((str(statement), parameters))
        if self.results:
            return self.results.pop(0)
        return FakeResult()

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


@pytest.fixture
def auth_token(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setattr(settings, "jwt_secret_key", "identity-management-test-key")
    return create_access_token({"sub": "5"})


def test_employee_create_is_parameterized_and_audited(
    monkeypatch: pytest.MonkeyPatch,
    auth_token: str,
) -> None:
    monkeypatch.setattr(
        "app.services.identidad.employees.request_service",
        lambda service, method, path, **kwargs: {"id_sede": 1},
    )
    employee = {
        "id_empleado": 22,
        "id_sede": 1,
        "num_documento": "DOC-22",
        "nombre_completo": "Empleado de prueba",
        "cargo": "Operador",
        "correo": None,
        "estado": "activo",
    }
    db = FakeDatabaseSession(FakeResult(employee), FakeResult())
    monkeypatch.setitem(app.dependency_overrides, get_identity_db, lambda: db)

    with TestClient(app) as client:
        response = client.post(
            "/employees",
            json={
                "id_sede": 1,
                "num_documento": "DOC-22",
                "nombre_completo": "Empleado de prueba",
                "cargo": "Operador",
                "correo": None,
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )

    assert response.status_code == 201
    assert response.json() == employee
    assert db.commits == 1
    assert db.statements[0][1]["num_documento"] == "DOC-22"
    assert "empleado_creado" in db.statements[1][1]["accion"]


def test_user_creation_hashes_password_and_never_returns_hash(
    monkeypatch: pytest.MonkeyPatch,
    auth_token: str,
) -> None:
    employee = {
        "id_empleado": 9,
        "id_sede": 1,
        "num_documento": "DOC-9",
        "nombre_completo": "Empleado",
        "cargo": "Asesor",
        "correo": None,
        "estado": "activo",
    }
    user = {
        "id_usuario": 11,
        "id_empleado": 9,
        "nombre_usuario": "nuevo",
        "estado": "activo",
        "fecha_creacion": "2026-01-01T10:00:00",
    }
    db = FakeDatabaseSession(FakeResult(employee), FakeResult(user), FakeResult())
    monkeypatch.setitem(app.dependency_overrides, get_identity_db, lambda: db)

    with TestClient(app) as client:
        response = client.post(
            "/users",
            json={
                "id_empleado": 9,
                "nombre_usuario": "nuevo",
                "password": "no-debe-regresarse",
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )

    assert response.status_code == 201
    assert "password_hash" not in response.json()
    assert "password" not in response.json()
    password_hash = db.statements[1][1]["password_hash"]
    assert password_hash.startswith("$argon2")
    assert db.statements[1][1]["password_hash"] != "no-debe-regresarse"
    assert db.commits == 1


def test_generic_user_update_rejects_password_fields(
    auth_token: str,
) -> None:
    with TestClient(app) as client:
        response = client.patch(
            "/users/5",
            json={"password": "not-allowed"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )

    assert response.status_code == 422


def test_password_change_requires_and_replaces_current_hash(
    monkeypatch: pytest.MonkeyPatch,
    auth_token: str,
) -> None:
    db = FakeDatabaseSession(
        FakeResult(
            {
                "id_usuario": 5,
                "id_empleado": 4,
                "nombre_usuario": "usuario",
                "password_hash": hash_password("actual"),
                "estado": "activo",
            }
        ),
        FakeResult(rowcount=1),
        FakeResult(),
    )
    monkeypatch.setitem(app.dependency_overrides, get_identity_db, lambda: db)

    with TestClient(app) as client:
        response = client.post(
            "/auth/password",
            json={"current_password": "actual", "new_password": "nueva"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )

    assert response.status_code == 204
    assert db.statements[1][1]["password_hash"].startswith("$argon2")
    assert db.statements[1][1]["password_hash"] != "nueva"
    assert db.commits == 1
