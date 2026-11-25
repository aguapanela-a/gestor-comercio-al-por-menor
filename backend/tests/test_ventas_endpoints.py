from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import create_access_token
from app.services.ventas.dependencies import get_ventas_db
from app.services.ventas.main import app


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

    def execute(self, statement, parameters=None):
        self.statements.append((str(statement), parameters))
        return self.results.pop(0) if self.results else FakeResult()

    def commit(self):
        self.commits += 1

    def rollback(self):
        pass


@pytest.fixture
def auth_token(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setattr(settings, "jwt_secret_key", "sales-test-signing-key")
    return create_access_token({"sub": "1"})


def test_customer_create_is_local_to_sales_database(
    monkeypatch: pytest.MonkeyPatch,
    auth_token: str,
) -> None:
    customer = {
        "id_cliente": 15,
        "tipo_documento": "CC",
        "num_documento": "10015",
        "nombre_completo": "Cliente",
        "correo": None,
        "telefono": None,
        "estado": "activo",
    }
    db = FakeDatabaseSession(FakeResult([customer]))
    monkeypatch.setitem(app.dependency_overrides, get_ventas_db, lambda: db)

    with TestClient(app) as client:
        response = client.post(
            "/customers",
            json={
                "tipo_documento": "CC",
                "num_documento": "10015",
                "nombre_completo": "Cliente",
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )

    assert response.status_code == 201
    assert response.json() == customer
    assert "ventas.clientes" in db.statements[0][0]
    assert db.commits == 1


def test_order_listing_uses_only_operational_fragments(
    monkeypatch: pytest.MonkeyPatch,
    auth_token: str,
) -> None:
    order = {
        "id_pedido": 21,
        "id_sede": 1,
        "id_almacen": 7,
        "id_cliente": 15,
        "id_empleado": 5,
        "fecha_pedido": datetime(2026, 1, 2),
        "estado": "pendiente",
        "total_registrado": "30.00",
    }
    db = FakeDatabaseSession(FakeResult([order]))
    monkeypatch.setitem(app.dependency_overrides, get_ventas_db, lambda: db)

    with TestClient(app) as client:
        response = client.get(
            "/orders",
            params={"id_sede": 1, "id_cliente": 15, "estado": "pendiente"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )

    assert response.status_code == 200
    assert response.json()[0]["id_pedido"] == 21
    query = db.statements[0][0]
    assert "ventas.pedidos_venta_sede_norte" in query
    assert "ventas.pedidos_venta_sede_sur" in query
    assert "ventas.pedidos_venta_sede_centro" in query
    assert "ventas.pedidos_venta_sede_distribucion" in query
    assert "pedidos_venta_respaldo_20261123" not in query
    assert not any(line.strip() == "FROM ventas.pedidos_venta" for line in query.splitlines())
    assert db.statements[0][1]["id_sede"] == 1


