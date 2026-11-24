from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import create_access_token
from app.services.compras.repositories import register_purchase_receipt
from app.services.inventarios.repositories import (
    adjust_inventory,
    dispatch_transfer,
    receive_transfer,
)
from app.services.ventas.dependencies import get_ventas_db
from app.services.ventas.main import app as ventas_app
from app.services.ventas.repositories import create_order, create_return


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


def test_retried_purchase_receipt_target_does_not_create_another_receipt() -> None:
    db = FakeDatabaseSession(
        FakeResult([{"id_orden_compra": 9, "estado": "recibida_parcial"}]),
        FakeResult(
            [
                {
                    "id_producto": 101,
                    "cantidad_solicitada": 5,
                    "cantidad_recibida": 2,
                }
            ]
        ),
    )

    result = register_purchase_receipt(
        db,
        id_orden_compra=9,
        received_totals={101: 2},
    )

    assert result["cantidades_actualizadas"] is False
    assert result["id_recepcion"] is None
    assert not any("INSERT INTO compras.recepciones_compra" in sql for sql, _ in db.statements)


def test_transfer_cannot_be_dispatched_twice() -> None:
    db = FakeDatabaseSession(
        FakeResult([{"id_transferencia": 4, "id_almacen_origen": 1, "estado": "despachada"}])
    )

    with pytest.raises(ValueError, match="solicitadas"):
        dispatch_transfer(db, 4)

    assert "FOR UPDATE" in db.statements[0][0]
    assert len(db.statements) == 1


def test_transfer_receipt_rejects_more_than_sent_before_stock_update() -> None:
    db = FakeDatabaseSession(
        FakeResult(
            [
                {
                    "id_transferencia": 4,
                    "id_almacen_destino": 2,
                    "estado": "despachada",
                }
            ]
        ),
        FakeResult(
            [
                {
                    "id_producto": 101,
                    "cantidad_enviada": 5,
                    "cantidad_recibida": 2,
                }
            ]
        ),
    )

    with pytest.raises(ValueError, match="supera"):
        receive_transfer(
            db,
            id_transferencia=4,
            id_sede_destino=1,
            received_totals={101: 6},
        )

    assert len(db.statements) == 2
    assert not any("UPDATE inventarios.inventarios" in sql for sql, _ in db.statements)


def test_partial_transfer_receipt_increments_only_received_delta() -> None:
    transfer = {
        "id_transferencia": 4,
        "id_almacen_origen": 1,
        "id_almacen_destino": 2,
        "fecha_solicitud": "2026-01-02",
        "fecha_despacho": "2026-01-02",
        "fecha_recepcion": None,
        "estado": "despachada",
    }
    db = FakeDatabaseSession(
        FakeResult(
            [
                {
                    "id_transferencia": 4,
                    "id_almacen_destino": 2,
                    "estado": "despachada",
                }
            ]
        ),
        FakeResult(
            [
                {
                    "id_producto": 101,
                    "cantidad_enviada": 5,
                    "cantidad_recibida": 0,
                },
                {
                    "id_producto": 102,
                    "cantidad_enviada": 3,
                    "cantidad_recibida": 0,
                },
            ]
        ),
        FakeResult([{"existencia_actual": 7}]),
        FakeResult(),
        FakeResult(),
        FakeResult([transfer]),
    )

    result = receive_transfer(
        db,
        id_transferencia=4,
        id_sede_destino=2,
        received_totals={101: 2},
    )

    stock_update = next(
        (sql, params)
        for sql, params in db.statements
        if "UPDATE inventarios.inventarios" in sql
    )
    assert stock_update[1]["delta"] == 2
    assert result["estado"] == "despachada"
    assert result["fecha_recepcion"] is None


def test_stock_adjustment_sets_absolute_target_under_row_lock() -> None:
    inventory = {
        "id_almacen": 7,
        "id_producto": 101,
        "id_sede": 1,
        "existencia_actual": 12,
        "stock_minimo": 10,
        "fecha_actualizacion": "2026-01-02",
    }
    db = FakeDatabaseSession(FakeResult(), FakeResult([inventory]))

    row = adjust_inventory(
        db,
        id_almacen=7,
        id_producto=101,
        id_sede=1,
        existencia_objetivo=12,
    )

    assert "FOR UPDATE" in db.statements[0][0]
    assert "ON CONFLICT (id_almacen, id_producto)" in db.statements[1][0]
    assert db.statements[1][1]["existencia_objetivo"] == 12
    assert row["existencia_actual"] == 12


def test_order_creation_uses_fixed_site_fragment_and_database_sequence() -> None:
    order = {
        "id_pedido": 21,
        "id_sede": 1,
        "id_almacen": 7,
        "id_cliente": 15,
        "id_empleado": 5,
        "fecha_pedido": "2026-01-02",
        "estado": "pendiente",
        "total_registrado": Decimal("12.50"),
    }
    db = FakeDatabaseSession(FakeResult([order]))

    result = create_order(
        db,
        id_sede=1,
        id_almacen=7,
        id_cliente=15,
        id_empleado=5,
        products=[
            {
                "id_producto": 101,
                "cantidad": 2,
                "precio_unitario": Decimal("6.25"),
            }
        ],
    )

    insert, parameters = db.statements[0]
    assert "INSERT INTO ventas.sede_norte_pedidos" in insert
    assert "id_pedido" not in insert.split("VALUES", 1)[0]
    assert parameters["total_registrado"] == Decimal("12.50")
    assert result["id_pedido"] == 21


def test_return_quantity_cannot_exceed_unreturned_sold_quantity() -> None:
    db = FakeDatabaseSession(
        FakeResult([{"id_producto": 101, "cantidad": 4}]),
        FakeResult([{"id_producto": 101, "cantidad": 5}]),
    )

    with pytest.raises(ValueError, match="supera"):
        create_return(
            db,
            id_pedido=21,
            motivo="Devolución",
            products=[
                {
                    "id_producto": 101,
                    "cantidad": 2,
                    "condicion_producto": "buen_estado",
                }
            ],
        )

    assert not any("INSERT INTO ventas.devoluciones" in sql for sql, _ in db.statements)


def test_payment_cannot_exceed_locked_order_balance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "jwt_secret_key", "business-flow-test-key")
    token = create_access_token({"sub": "1"})
    order = {
        "id_pedido": 22,
        "id_sede": 2,
        "id_almacen": 8,
        "id_cliente": 15,
        "id_empleado": 5,
        "fecha_pedido": "2026-01-02",
        "estado": "pendiente",
        "total_registrado": Decimal("100.00"),
    }
    db = FakeDatabaseSession(
        FakeResult(),
        FakeResult(),
        FakeResult([order]),
        FakeResult([order]),
        FakeResult([{"pagado": Decimal("90.00")}]),
    )
    monkeypatch.setitem(ventas_app.dependency_overrides, get_ventas_db, lambda: db)

    with TestClient(ventas_app) as client:
        response = client.post(
            "/orders/22/payments",
            json={"valor": "10.01", "medio_pago": "efectivo"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 409
    assert not any("INSERT INTO ventas.pagos" in sql for sql, _ in db.statements)
    assert db.commits == 0
    assert db.rollbacks == 1
