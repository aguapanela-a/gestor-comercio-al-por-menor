from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import create_access_token
from app.services.inventarios.dependencies import get_inventarios_db
from app.services.inventarios.main import app as inventarios_app
from app.services.inventarios.repositories import (
    dispatch_sales_order,
    register_sales_return,
)
from app.services.ventas.dependencies import get_ventas_db
from app.services.ventas.main import app as ventas_app
from app.shared.exceptions import RemoteServiceError


class FakeResult:
    def __init__(self, rows: list[dict[str, Any]] | None = None) -> None:
        self.rows = rows or []

    def mappings(self):
        return self

    def first(self):
        return self.rows[0] if self.rows else None

    def one(self):
        return self.rows[0]

    def scalar_one_or_none(self):
        if not self.rows:
            return None
        row = self.rows[0]
        return next(iter(row.values())) if isinstance(row, dict) else row


class FakeDatabaseSession:
    def __init__(self, *results: FakeResult) -> None:
        self.results = list(results)
        self.statements: list[tuple[str, Any]] = []
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
    monkeypatch.setattr(settings, "jwt_secret_key", "sales-return-test-signing-key")
    return create_access_token({"sub": "1"})


def test_inventory_return_increments_stock_and_records_idempotency_first(
    monkeypatch: pytest.MonkeyPatch,
    auth_token: str,
) -> None:
    db = FakeDatabaseSession(
        FakeResult(),
        FakeResult(),
        FakeResult([{"id_devolucion": 41}]),
        FakeResult([{"id_producto": 101}]),
    )
    monkeypatch.setitem(
        inventarios_app.dependency_overrides,
        get_inventarios_db,
        lambda: db,
    )
    monkeypatch.setattr(
        "app.services.inventarios.stock.request_service",
        lambda *args, **kwargs: {"id_almacen": 7, "id_sede": 2},
    )

    with TestClient(inventarios_app) as client:
        response = client.post(
            "/stock/sales-returns",
            json={
                "id_devolucion": 41,
                "id_pedido": 22,
                "id_sede": 2,
                "id_almacen": 7,
                "productos": [{"id_producto": 101, "cantidad": 3}],
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )

    assert response.status_code == 200
    assert response.json()["already_returned"] is False
    assert "INSERT INTO inventarios.devoluciones_venta" in db.statements[2][0]
    assert "ON CONFLICT (id_devolucion) DO NOTHING" in db.statements[2][0]
    assert "UPDATE inventarios.inventarios" in db.statements[3][0]
    assert db.statements[3][1]["cantidad"] == 3
    assert "fecha_actualizacion = CURRENT_TIMESTAMP" in db.statements[3][0]
    assert db.commits == 1


def test_processed_inventory_return_is_idempotent() -> None:
    db = FakeDatabaseSession(
        FakeResult(),
        FakeResult(
            [
                {
                    "id_pedido": 22,
                    "id_sede": 2,
                    "id_almacen": 7,
                    "productos": [{"id_producto": 101, "cantidad": 3}],
                }
            ]
        ),
    )

    result = register_sales_return(
        db,
        id_devolucion=41,
        id_pedido=22,
        id_sede=2,
        id_almacen=7,
        products=[{"id_producto": 101, "cantidad": 3}],
    )

    assert result["already_returned"] is True
    assert not any(
        "UPDATE inventarios.inventarios" in sql
        for sql, _ in db.statements
    )


def test_inventory_return_conflicts_when_retried_with_different_data() -> None:
    db = FakeDatabaseSession(
        FakeResult(),
        FakeResult(
            [
                {
                    "id_pedido": 22,
                    "id_sede": 2,
                    "id_almacen": 7,
                    "productos": [{"id_producto": 101, "cantidad": 3}],
                }
            ]
        ),
    )

    with pytest.raises(ValueError, match="datos diferentes"):
        register_sales_return(
            db,
            id_devolucion=41,
            id_pedido=22,
            id_sede=2,
            id_almacen=7,
            products=[{"id_producto": 101, "cantidad": 4}],
        )

    assert not any(
        "UPDATE inventarios.inventarios" in sql
        for sql, _ in db.statements
    )


def test_paid_order_dispatch_still_decrements_inventory() -> None:
    db = FakeDatabaseSession(
        FakeResult([{"id_pedido": 22}]),
        FakeResult([{"existencia_actual": 9}]),
        FakeResult(),
    )

    result = dispatch_sales_order(
        db,
        id_pedido=22,
        id_sede=2,
        id_almacen=7,
        products=[{"id_producto": 101, "cantidad": 3}],
    )

    assert result["already_dispatched"] is False
    assert "INSERT INTO inventarios.despachos_venta" in db.statements[0][0]
    assert "existencia_actual = existencia_actual - :cantidad" in db.statements[2][0]
    assert db.statements[2][1]["cantidad"] == 3


@pytest.mark.parametrize(
    ("condition", "expected_products"),
    [
        ("buen_estado", [{"id_producto": 101, "cantidad": 2}]),
        ("defectuoso", []),
        ("empaque_abierto", []),
    ],
)
def test_sales_approval_sends_only_good_condition_products(
    monkeypatch: pytest.MonkeyPatch,
    auth_token: str,
    condition: str,
    expected_products: list[dict[str, int]],
) -> None:
    from app.services.ventas import returns as returns_service

    pending = {
        "id_devolucion": 41,
        "id_pedido": 22,
        "fecha_solicitud": "2026-01-02",
        "motivo": "Motivo",
        "estado": "pendiente",
    }
    db = FakeDatabaseSession()
    monkeypatch.setitem(ventas_app.dependency_overrides, get_ventas_db, lambda: db)
    monkeypatch.setattr(returns_service, "get_return", lambda *args: pending)
    monkeypatch.setattr(
        returns_service,
        "resolve_return",
        lambda *args, **kwargs: {**pending, "estado": "aprobada"},
    )
    monkeypatch.setattr(
        returns_service,
        "get_order",
        lambda *args: {"id_sede": 2, "id_almacen": 7},
    )
    monkeypatch.setattr(
        returns_service,
        "list_return_details",
        lambda *args: [
            {
                "id_producto": 101,
                "cantidad": 2,
                "condicion_producto": condition,
            }
        ],
    )
    requests = []
    inventory_db = FakeDatabaseSession(
        FakeResult([{"id_devolucion": 41}]),
        FakeResult([{"id_producto": 101}]),
    )

    def fake_request(service, method, path, **kwargs):
        requests.append((service, method, path, kwargs["json_body"]))
        payload = kwargs["json_body"]
        return register_sales_return(
            inventory_db,
            id_devolucion=payload["id_devolucion"],
            id_pedido=payload["id_pedido"],
            id_sede=payload["id_sede"],
            id_almacen=payload["id_almacen"],
            products=payload["productos"],
        )

    monkeypatch.setattr(returns_service, "request_service", fake_request)

    with TestClient(ventas_app) as client:
        response = client.post(
            "/returns/41/approve",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

    assert response.status_code == 200
    assert len(requests) == 1
    assert requests[0][0:3] == (
        "inventarios",
        "POST",
        "/stock/sales-returns",
    )
    assert requests[0][3]["productos"] == expected_products
    assert requests[0][3]["id_pedido"] == 22
    assert requests[0][3]["id_sede"] == 2
    assert requests[0][3]["id_almacen"] == 7
    stock_updates = [
        parameters
        for sql, parameters in inventory_db.statements
        if "UPDATE inventarios.inventarios" in sql
    ]
    assert len(stock_updates) == (1 if condition == "buen_estado" else 0)
    assert db.commits == 1


def test_inventory_failure_rolls_back_return_approval(
    monkeypatch: pytest.MonkeyPatch,
    auth_token: str,
) -> None:
    from app.services.ventas import returns as returns_service

    pending = {
        "id_devolucion": 41,
        "id_pedido": 22,
        "fecha_solicitud": "2026-01-02",
        "motivo": "Motivo",
        "estado": "pendiente",
    }
    db = FakeDatabaseSession()
    monkeypatch.setitem(ventas_app.dependency_overrides, get_ventas_db, lambda: db)
    monkeypatch.setattr(returns_service, "get_return", lambda *args: pending)
    monkeypatch.setattr(
        returns_service,
        "resolve_return",
        lambda *args, **kwargs: {**pending, "estado": "aprobada"},
    )
    monkeypatch.setattr(
        returns_service,
        "get_order",
        lambda *args: {"id_sede": 2, "id_almacen": 7},
    )
    monkeypatch.setattr(
        returns_service,
        "list_return_details",
        lambda *args: [
            {
                "id_producto": 101,
                "cantidad": 2,
                "condicion_producto": "buen_estado",
            }
        ],
    )
    monkeypatch.setattr(
        returns_service,
        "request_service",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            RemoteServiceError("inventarios", 503, "not available")
        ),
    )

    with TestClient(ventas_app) as client:
        response = client.post(
            "/returns/41/approve",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

    assert response.status_code == 503
    assert db.commits == 0
    assert db.rollbacks == 1


def test_rejecting_return_does_not_call_inventory(
    monkeypatch: pytest.MonkeyPatch,
    auth_token: str,
) -> None:
    from app.services.ventas import returns as returns_service

    pending = {
        "id_devolucion": 41,
        "id_pedido": 22,
        "fecha_solicitud": "2026-01-02",
        "motivo": "Motivo",
        "estado": "pendiente",
    }
    db = FakeDatabaseSession()
    monkeypatch.setitem(ventas_app.dependency_overrides, get_ventas_db, lambda: db)
    monkeypatch.setattr(returns_service, "get_return", lambda *args: pending)
    monkeypatch.setattr(
        returns_service,
        "resolve_return",
        lambda *args, **kwargs: {**pending, "estado": "rechazada"},
    )
    inventory_calls = []
    monkeypatch.setattr(
        returns_service,
        "request_service",
        lambda *args, **kwargs: inventory_calls.append(args),
    )

    with TestClient(ventas_app) as client:
        response = client.post(
            "/returns/41/reject",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

    assert response.status_code == 200
    assert response.json()["estado"] == "rechazada"
    assert inventory_calls == []
    assert db.commits == 1
