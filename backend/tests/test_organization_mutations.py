import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import create_access_token
from app.services.organizacion.dependencies import get_organizacion_db
from app.services.organizacion.main import app


class FakeResult:
    def __init__(self, rows=None) -> None:
        self.rows = rows or []

    def mappings(self):
        return self

    def first(self):
        return self.rows[0] if self.rows else None

    def one(self):
        return self.rows[0]


class FakeDatabaseSession:
    def __init__(self, *results) -> None:
        self.results = list(results)
        self.statements = []
        self.commits = 0

    def execute(self, statement, parameters=None):
        self.statements.append((str(statement), parameters))
        return self.results.pop(0) if self.results else FakeResult()

    def commit(self):
        self.commits += 1

    def rollback(self):
        pass


@pytest.fixture
def auth_token(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setattr(settings, "jwt_secret_key", "organization-mutation-test-key")
    return create_access_token({"sub": "1"})


def test_warehouse_creation_validates_site_and_preserves_unique_key_behavior(
    monkeypatch: pytest.MonkeyPatch,
    auth_token: str,
) -> None:
    warehouse = {
        "id_almacen": 7,
        "id_sede": 4,
        "nombre": "Almacén Principal",
        "tipo_almacen": "principal",
        "estado": "activo",
    }
    db = FakeDatabaseSession(FakeResult([{"1": 1}]), FakeResult([warehouse]))
    monkeypatch.setitem(app.dependency_overrides, get_organizacion_db, lambda: db)

    with TestClient(app) as client:
        response = client.post(
            "/warehouses",
            json={
                "id_sede": 4,
                "nombre": "Almacén Principal",
                "tipo_almacen": "principal",
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )

    assert response.status_code == 201
    assert "organizacion.sedes" in db.statements[0][0]
    assert "organizacion.almacenes" in db.statements[1][0]
    assert db.commits == 1


def test_site_delete_is_a_soft_deactivation(
    monkeypatch: pytest.MonkeyPatch,
    auth_token: str,
) -> None:
    db = FakeDatabaseSession(
        FakeResult(
            [
                {
                    "id_sede": 2,
                    "nombre": "Sede",
                    "ciudad": "Cali",
                    "direccion": "Centro",
                    "tipo_sede": "comercial",
                    "estado": "inactivo",
                }
            ]
        ),
        FakeResult(
            [
                {
                    "id_sede": 2,
                    "nombre": "Sede",
                    "ciudad": "Cali",
                    "direccion": "Centro",
                    "tipo_sede": "comercial",
                    "estado": "inactivo",
                }
            ]
        )
    )
    monkeypatch.setitem(app.dependency_overrides, get_organizacion_db, lambda: db)

    with TestClient(app) as client:
        response = client.delete(
            "/sedes/2",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

    assert response.status_code == 204
    assert "UPDATE organizacion.sedes" in db.statements[1][0]
    assert db.statements[1][1]["estado"] == "inactivo"
