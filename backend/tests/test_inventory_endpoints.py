from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import create_access_token
from app.services.inventarios.dependencies import get_inventarios_db
from app.services.inventarios.main import app


class FakeResult:
    def __init__(self, rows=None) -> None:
        self.rows = rows or []

    def mappings(self):
        return self

    def all(self):
        return self.rows

    def first(self):
        return self.rows[0] if self.rows else None


class FakeDatabaseSession:
    def __init__(self, *results) -> None:
        self.results = list(results)
        self.statements = []
        self.commits = 0
        self.rollbacks = 0

    def execute(self, statement, parameters=None):
        self.statements.append((str(statement), parameters))
        return self.results.pop(0) if self.results else FakeResult()

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


@pytest.fixture
def auth_token(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setattr(settings, "jwt_secret_key", "inventory-test-signing-key")
    return create_access_token({"sub": "1"})


def test_stock_list_uses_filters_and_limits(
    monkeypatch: pytest.MonkeyPatch,
    auth_token: str,
) -> None:
    db = FakeDatabaseSession(
        FakeResult(
            [
                {
                    "id_almacen": 7,
                    "id_producto": 4,
                    "id_sede": 1,
                    "existencia_actual": 2,
                    "stock_minimo": 5,
                    "fecha_actualizacion": datetime(2026, 1, 1),
                }
            ]
        )
    )
    monkeypatch.setitem(app.dependency_overrides, get_inventarios_db, lambda: db)

    with TestClient(app) as client:
        response = client.get(
            "/stock",
            params={"id_producto": 4, "id_sede": 1, "bajo_minimo": "true"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )

    assert response.status_code == 200
    assert response.json()[0]["existencia_actual"] == 2
    query, parameters = db.statements[0]
    assert "existencia_actual <= stock_minimo" in query
    assert parameters == {
        "id_producto": 4,
        "id_sede": 1,
        "limit": 50,
        "offset": 0,
    }


def test_set_stock_minimum_validates_remote_references(
    monkeypatch: pytest.MonkeyPatch,
    auth_token: str,
) -> None:
    row = {
        "id_almacen": 7,
        "id_producto": 4,
        "id_sede": 1,
        "existencia_actual": 9,
        "stock_minimo": 12,
        "fecha_actualizacion": datetime(2026, 1, 1),
    }
    db = FakeDatabaseSession(FakeResult([row]))
    monkeypatch.setitem(app.dependency_overrides, get_inventarios_db, lambda: db)
    calls = []

    def fake_request(service, method, path, **kwargs):
        calls.append((service, method, path))
        return {"id_producto": 4} if service == "catalogo" else {"id_almacen": 7}

    monkeypatch.setattr("app.services.inventarios.stock.request_service", fake_request)

    with TestClient(app) as client:
        response = client.patch(
            "/stock/minimum",
            json={"id_almacen": 7, "id_producto": 4, "stock_minimo": 12},
            headers={"Authorization": f"Bearer {auth_token}"},
        )

    assert response.status_code == 200
    assert calls == [
        ("catalogo", "GET", "/products/4"),
        ("organizacion", "GET", "/warehouses/7"),
    ]
    assert "id_almacen = :id_almacen" in db.statements[0][0]
    assert db.commits == 1


def test_transfer_details_return_404_for_missing_transfer(
    monkeypatch: pytest.MonkeyPatch,
    auth_token: str,
) -> None:
    db = FakeDatabaseSession(FakeResult())
    monkeypatch.setitem(app.dependency_overrides, get_inventarios_db, lambda: db)

    with TestClient(app) as client:
        response = client.get(
            "/transfers/88/details",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

    assert response.status_code == 404
    assert len(db.statements) == 1
