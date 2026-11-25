from typing import Any

from fastapi import Depends
from psycopg import Connection

from app.services.reportes.aplicacion.puertos_entrada import InPortViews
from app.services.reportes.aplicacion.registryStrategy import DynamicViewDispatcher
from app.services.reportes.aplicacion.useCases import UseCaseViews
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


def get_use_case_views(
    connection: Connection[Any] = Depends(get_connection),
) -> InPortViews:
    views = [
        VistaInventarioPorSede(connection),
        VistaAlertasReabastecimiento(connection),
        VistaProductosSinInventario(connection),
        VistaVentasMensualesPorSede(connection),
        VistaPedidosPendientes(connection),
        VistaSaldosPendientes(connection),
        VistaComprasPendientes(connection),
        VistaTransferenciasEnTransito(connection),
        VistaDevolucionesPorProducto(connection),
        VistaReporteCorporativo(connection),
    ]
    return UseCaseViews(DynamicViewDispatcher(views))
