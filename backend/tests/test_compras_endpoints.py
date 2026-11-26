import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import create_access_token
from app.services.compras.dependencies import get_compras_db
from app.services.compras.main import app


class FakeResult:
    def __init__(self, rows=None) -> None:
        self.rows = rows or []

    def mappings(self):
        return self

    def all(self):
        return self.rows

    def first(self):
        return self.rows[0] if self.rows else None

    def one(self):
        return self.rows[0]


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
    monkeypatch.setattr(settings, "jwt_secret_key", "purchase-test-signing-key")
    return create_access_token({"sub": "1"})


def test_purchase_endpoints_require_jwt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = FakeDatabaseSession()
    monkeypatch.setitem(app.dependency_overrides, get_compras_db, lambda: db)

    with TestClient(app) as client:
        response = client.get("/suppliers")

    assert response.status_code == 401
    assert db.statements == []


def test_supplier_create_returns_only_supplier_fields(
    monkeypatch: pytest.MonkeyPatch,
    auth_token: str,
) -> None:
    supplier = {
        "id_proveedor": 8,
        "identificacion": "SUP-8",
        "razon_social": "Proveedor Uno",
        "ciudad": None,
        "correo": None,
        "telefono": None,
        "estado": "activo",
    }
    db = FakeDatabaseSession(FakeResult([supplier]))
    monkeypatch.setitem(app.dependency_overrides, get_compras_db, lambda: db)

    with TestClient(app) as client:
        response = client.post(
            "/suppliers",
            json={
                "identificacion": "SUP-8",
                "razon_social": "Proveedor Uno",
                "estado": "activo",
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )

    assert response.status_code == 201
    assert response.json() == supplier
    assert db.statements[0][1]["identificacion"] == "SUP-8"
    assert db.commits == 1


def test_order_detail_404_when_missing(
    monkeypatch: pytest.MonkeyPatch,
    auth_token: str,
) -> None:
    db = FakeDatabaseSession(FakeResult())
    monkeypatch.setitem(app.dependency_overrides, get_compras_db, lambda: db)

    with TestClient(app) as client:
        response = client.get(
            "/purchase-orders/404/details",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

    assert response.status_code == 404
    assert len(db.statements) == 1


def test_product_supplier_write_checks_catalog_service(
    monkeypatch: pytest.MonkeyPatch,
    auth_token: str,
) -> None:
    supplier = {
        "id_proveedor": 8,
        "identificacion": "SUP-8",
        "razon_social": "Proveedor Uno",
        "ciudad": None,
        "correo": None,
        "telefono": None,
        "estado": "activo",
    }
    relation = {
        "id_producto": 4,
        "id_proveedor": 8,
        "costo_referencia": "25.50",
        "plazo_entrega_dias": 3,
        "estado": "activo",
    }
    db = FakeDatabaseSession(FakeResult(), FakeResult([supplier]), FakeResult([relation]))
    monkeypatch.setitem(app.dependency_overrides, get_compras_db, lambda: db)
    calls = []

    def fake_request(service, method, path, **kwargs):
        calls.append((service, method, path))
        return {"id_producto": 4, "estado": "activo"}

    monkeypatch.setattr("app.services.compras.suppliers.request_service", fake_request)

    with TestClient(app) as client:
        response = client.put(
            "/product-suppliers/4/8",
            json={
                "costo_referencia": "25.50",
                "plazo_entrega_dias": 3,
                "estado": "activo",
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )

    assert response.status_code == 200
    assert calls == [("catalogo", "GET", "/products/4")]
    assert "ON CONFLICT (id_producto, id_proveedor)" in db.statements[2][0]
    assert db.commits == 1
