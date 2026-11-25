from types import SimpleNamespace
from unittest.mock import MagicMock
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient
from psycopg.sql import Composed

from app.services.reportes.aplicacion.useCases import UseCaseViews
from app.services.reportes.infraestructura.adaptadores_entrada.dependencies import (
    get_use_case_views,
)
from app.services.reportes.infraestructura.adaptadores_salida.report_view_catalog import (
    REPORTS_SCHEMA,
)
from app.services.reportes.infraestructura.adaptadores_salida import (
    VistaAlertasReabastecimiento,
    VistaComprasPendientes,
    VistaDevolucionesPorProducto,
    VistaInventarioPorSede,
    VistaPedidosPendientes,
    VistaProductosSinInventario,
    VistaReporteCorporativo,
    VistaSaldosPendientes,
    VistaTransferenciasEnTransito,
    VistaVentasMensualesPorSede,
)
from app.services.reportes.infraestructura.configuracion import get_connection
from app.services.reportes.main import app


def test_reportes_health(assert_health_endpoints) -> None:
    assert_health_endpoints(app, "reportes")


def test_database_health_reports_unavailable_without_connecting(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "app.shared.api.check_database_connection",
        lambda _service: {
            "service": "reportes",
            "connected": False,
            "error": "Falta configuración de prueba",
        },
    )
    with TestClient(app) as client:
        response = client.get("/health/database")

    assert response.status_code == 503
    assert response.json()["detail"]["database"] == "disconnected"


@pytest.mark.parametrize(
    ("path", "entity_name", "row"),
    [
        (
            "/vista_inventario_por_sede",
            "vista_inventario_por_sede",
            {
                "id_sede": 1,
                "sede": "Centro",
                "id_almacen": 2,
                "almacen": "Principal",
                "id_producto": 3,
                "sku": "SKU-3",
                "producto": "Producto",
                "categoria": "General",
                "existencia_actual": 20,
                "stock_minimo": 5,
                "precio_lista": 1000,
                "valorizacion_estimada": 20000,
            },
        ),
        (
            "/vista_alertas_reabastecimiento",
            "vista_alertas_reabastecimiento",
            {
                "id_sede": 1,
                "sede": "Centro",
                "id_almacen": 2,
                "almacen": "Principal",
                "id_producto": 3,
                "sku": "SKU-3",
                "producto": "Producto",
                "existencia_actual": 0,
                "stock_minimo": 5,
                "faltante": 5,
                "nivel_alerta": "SIN EXISTENCIA",
            },
        ),
        (
            "/vista_productos_sin_inventario",
            "vista_productos_sin_inventario",
            {
                "id_sede": 1,
                "sede": "Centro",
                "id_producto": 3,
                "sku": "SKU-3",
                "producto": "Producto",
            },
        ),
        (
            "/vista_ventas_mensuales_por_sede",
            "vista_ventas_mensuales_por_sede",
            {
                "id_sede": 1,
                "sede": "Centro",
                "mes": "2026-10-01",
                "pedidos": 20,
                "total_vendido": 50000,
                "total_mes_anterior": None,
                "variacion": None,
                "variacion_pct": None,
            },
        ),
        (
            "/vista_pedidos_pendientes",
            "vista_pedidos_pendientes",
            {
                "id_pedido": 4,
                "id_sede": 1,
                "sede": "Centro",
                "id_almacen": 2,
                "almacen": "Principal",
                "id_cliente": 5,
                "cliente": "Cliente",
                "id_empleado": None,
                "vendedor": None,
                "fecha_pedido": "2026-11-24",
                "dias_antiguedad": 1,
                "total_registrado": 12000,
            },
        ),
        (
            "/vista_saldos_pendientes",
            "vista_saldos_pendientes",
            {
                "id_pedido": 4,
                "id_sede": 1,
                "sede": "Centro",
                "id_cliente": 5,
                "cliente": "Cliente",
                "fecha_pedido": "2026-11-24",
                "total_registrado": 12000,
                "pagos_confirmados": 2000,
                "saldo_pendiente": 10000,
            },
        ),
        (
            "/vista_compras_pendientes",
            "vista_compras_pendientes",
            {
                "id_orden_compra": 6,
                "proveedor": "Proveedor",
                "id_almacen_destino": 2,
                "almacen_destino": "Principal",
                "fecha_orden": "2026-11-20",
                "fecha_estimada": None,
                "estado_orden": "enviada",
                "id_producto": 3,
                "producto": "Producto",
                "cantidad_solicitada": 10,
                "cantidad_recibida": 4,
                "cantidad_pendiente": 6,
            },
        ),
        (
            "/vista_transferencias_en_transito",
            "vista_transferencias_en_transito",
            {
                "id_transferencia": 7,
                "id_almacen_origen": 2,
                "almacen_origen": "Norte",
                "sede_origen": "Norte",
                "id_almacen_destino": 8,
                "almacen_destino": "Sur",
                "sede_destino": "Sur",
                "fecha_despacho": "2026-11-23",
                "dias_transcurridos": 2,
                "id_producto": 3,
                "producto": "Producto",
                "cantidad_enviada": 5,
            },
        ),
        (
            "/vista_devoluciones_por_producto",
            "vista_devoluciones_por_producto",
            {
                "id_producto": 3,
                "sku": "SKU-3",
                "producto": "Producto",
                "categoria": "General",
                "cantidad_vendida": 100,
                "cantidad_devuelta": 2,
                "porcentaje_devolucion": 2,
            },
        ),
        (
            "/vista_reporte_corporativo",
            "vista_reporte_corporativo",
            {
                "id_sede": 1,
                "sede": "Centro",
                "tipo_sede": "principal",
                "productos_activos": 20,
                "unidades_inventario": 150,
                "ventas_total": 500000,
                "pedidos_pendientes": 2,
                "ordenes_compra": 3,
                "valor_compras": 125000,
                "transferencias_enviadas": 4,
                "transferencias_recibidas": 3,
            },
        ),
    ],
)
def test_report_view_endpoints_return_mapped_rows(
    path: str,
    entity_name: str,
    row: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    out_port = MagicMock()
    out_port.getView.return_value = [row]
    monkeypatch.setitem(
        app.dependency_overrides,
        get_use_case_views,
        lambda: UseCaseViews(out_port),
    )

    with TestClient(app) as client:
        response = client.get(path)

    assert response.status_code == 200
    assert response.json() == [row]
    out_port.getView.assert_called_once_with(entity_name)


@pytest.mark.parametrize(
    ("adapter_type", "entity_name"),
    [
        (VistaInventarioPorSede, "vista_inventario_por_sede"),
        (VistaAlertasReabastecimiento, "vista_alertas_reabastecimiento"),
        (VistaProductosSinInventario, "vista_productos_sin_inventario"),
        (VistaVentasMensualesPorSede, "vista_ventas_mensuales_por_sede"),
        (VistaPedidosPendientes, "vista_pedidos_pendientes"),
        (VistaSaldosPendientes, "vista_saldos_pendientes"),
        (VistaComprasPendientes, "vista_compras_pendientes"),
        (VistaTransferenciasEnTransito, "vista_transferencias_en_transito"),
        (VistaDevolucionesPorProducto, "vista_devoluciones_por_producto"),
        (VistaReporteCorporativo, "vista_reporte_corporativo"),
    ],
)
def test_report_view_adapters_query_and_map_rows(
    adapter_type: type,
    entity_name: str,
) -> None:
    cursor = MagicMock()
    cursor.__enter__.return_value = cursor
    cursor.description = [
        SimpleNamespace(name="id_producto"),
        SimpleNamespace(name="producto"),
    ]
    cursor.fetchall.return_value = [{"id_producto": 3, "producto": "Producto"}]
    connection = MagicMock()
    connection.cursor.return_value = cursor

    adapter = adapter_type(connection)

    assert adapter.getEntityName() == entity_name
    assert adapter.getViewOut() == [{"id_producto": 3, "producto": "Producto"}]
    cursor.execute.assert_called_once_with(
        f"SELECT * FROM reportes.{entity_name};"
    )


def _report_catalog_row(name: str) -> dict[str, object]:
    return {
        "name": name,
        "schema_name": REPORTS_SCHEMA,
        "description": None,
        "columns": [
            {
                "name": "total",
                "type": "numeric",
                "nullable": True,
                "description": None,
            }
        ],
    }


def _report_connection() -> tuple[MagicMock, MagicMock]:
    cursor = MagicMock()
    cursor.__enter__.return_value = cursor
    connection = MagicMock()
    connection.info.encoding = "utf-8"
    connection.cursor.return_value = cursor
    connection.escape_identifier.side_effect = lambda value: f'"{value}"'
    return connection, cursor


def test_report_catalog_returns_every_authorized_view_and_refreshes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection, cursor = _report_connection()
    initial_views = [_report_catalog_row(f"vista_reporte_{index}") for index in range(15)]
    updated_views = [*initial_views, _report_catalog_row("vista_reporte_nueva")]
    cursor.fetchall.side_effect = [initial_views, updated_views]
    monkeypatch.setitem(app.dependency_overrides, get_connection, lambda: connection)

    with TestClient(app) as client:
        first_response = client.get("/vistas")
        second_response = client.get("/vistas")

    assert first_response.status_code == 200
    assert len(first_response.json()) == 15
    assert first_response.json()[0] == {
        "name": "vista_reporte_0",
        "schema": REPORTS_SCHEMA,
        "description": None,
        "columns": initial_views[0]["columns"],
        "label": "Reporte 0",
    }
    assert second_response.status_code == 200
    assert len(second_response.json()) == 16
    assert second_response.json()[-1]["name"] == "vista_reporte_nueva"
    assert cursor.execute.call_count == 2

    query, parameters = cursor.execute.call_args.args
    assert parameters == (REPORTS_SCHEMA,)
    assert "c.relkind = 'v'" in query
    assert "has_schema_privilege" in query
    assert "has_table_privilege" in query
    assert "LIMIT" not in query.upper()


def test_dynamic_report_endpoint_queries_authorized_view_safely(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection, cursor = _report_connection()
    cursor.fetchone.return_value = {"name": "vista_nueva"}
    cursor.fetchall.return_value = [{"total": 123.45}]
    cursor.description = [SimpleNamespace(name="total")]
    monkeypatch.setitem(app.dependency_overrides, get_connection, lambda: connection)

    with TestClient(app) as client:
        response = client.get("/vistas/vista_nueva")

    assert response.status_code == 200
    assert response.json() == [{"total": 123.45}]
    assert cursor.execute.call_count == 2
    query = cursor.execute.call_args.args[0]
    assert isinstance(query, Composed)
    assert query._obj[1]._obj == ("reportes",)
    assert query._obj[3]._obj == ("vista_nueva",)


@pytest.mark.parametrize(
    "view_name",
    [
        "vista_inexistente",
        "public.vista_inventario_por_sede",
        'vista_x"; DROP TABLE reportes.vista_inventario_por_sede;--',
    ],
)
def test_dynamic_report_endpoint_rejects_unknown_schemas_and_injection(
    view_name: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection, cursor = _report_connection()
    cursor.fetchone.return_value = None
    monkeypatch.setitem(app.dependency_overrides, get_connection, lambda: connection)

    with TestClient(app) as client:
        response = client.get(f"/vistas/{quote(view_name, safe='')}")

    assert response.status_code == 404
    assert cursor.execute.call_count == 1
    query, parameters = cursor.execute.call_args.args
    assert "c.relkind = 'v'" in query
    assert parameters == (REPORTS_SCHEMA, view_name)
