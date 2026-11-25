from collections.abc import Callable
from typing import TypeVar

from fastapi import APIRouter, Depends, HTTPException, status

from app.services.reportes.aplicacion.puertos_entrada import InPortViews
from app.services.reportes.infraestructura.adaptadores_entrada.dependencies import (
    get_use_case_views,
)
from app.services.reportes.nucleo.modelos import (
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

T = TypeVar("T")


class GetViewInAdapter:
    def __init__(self) -> None:
        self.router = APIRouter(tags=["Reportes"])
        self.router.add_api_route(
            "/vista_inventario_por_sede",
            self.get_vista_inventario_por_sede,
            methods=["GET"],
            response_model=None,
        )
        self.router.add_api_route(
            "/vista_alertas_reabastecimiento",
            self.get_vista_alertas_reabastecimiento,
            methods=["GET"],
            response_model=None,
        )
        self.router.add_api_route(
            "/vista_productos_sin_inventario",
            self.get_vista_productos_sin_inventario,
            methods=["GET"],
            response_model=None,
        )
        self.router.add_api_route(
            "/vista_ventas_mensuales_por_sede",
            self.get_vista_ventas_mensuales_por_sede,
            methods=["GET"],
            response_model=None,
        )
        self.router.add_api_route(
            "/vista_pedidos_pendientes",
            self.get_vista_pedidos_pendientes,
            methods=["GET"],
            response_model=None,
        )
        self.router.add_api_route(
            "/vista_saldos_pendientes",
            self.get_vista_saldos_pendientes,
            methods=["GET"],
            response_model=None,
        )
        self.router.add_api_route(
            "/vista_compras_pendientes",
            self.get_vista_compras_pendientes,
            methods=["GET"],
            response_model=None,
        )
        self.router.add_api_route(
            "/vista_transferencias_en_transito",
            self.get_vista_transferencias_en_transito,
            methods=["GET"],
            response_model=None,
        )
        self.router.add_api_route(
            "/vista_devoluciones_por_producto",
            self.get_vista_devoluciones_por_producto,
            methods=["GET"],
            response_model=None,
        )
        self.router.add_api_route(
            "/vista_reporte_corporativo",
            self.get_vista_reporte_corporativo,
            methods=["GET"],
            response_model=None,
        )

    @staticmethod
    def _execute(operation: Callable[[], T]) -> T:
        try:
            return operation()
        except NotImplementedError as error:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=str(error),
            ) from error

    def get_vista_inventario_por_sede(
        self, use_case: InPortViews = Depends(get_use_case_views)
    ) -> list[VistaInventarioPorSede]:
        return self._execute(use_case.get_vista_inventario_por_sede)

    def get_vista_alertas_reabastecimiento(
        self, use_case: InPortViews = Depends(get_use_case_views)
    ) -> list[VistaAlertasReabastecimiento]:
        return self._execute(use_case.get_vista_alertas_reabastecimiento)

    def get_vista_productos_sin_inventario(
        self, use_case: InPortViews = Depends(get_use_case_views)
    ) -> list[VistaProductosSinInventario]:
        return self._execute(use_case.get_vista_productos_sin_inventario)

    def get_vista_ventas_mensuales_por_sede(
        self, use_case: InPortViews = Depends(get_use_case_views)
    ) -> list[VistaVentasMensualesPorSede]:
        return self._execute(use_case.get_vista_ventas_mensuales_por_sede)

    def get_vista_pedidos_pendientes(
        self, use_case: InPortViews = Depends(get_use_case_views)
    ) -> list[VistaPedidosPendientes]:
        return self._execute(use_case.get_vista_pedidos_pendientes)

    def get_vista_saldos_pendientes(
        self, use_case: InPortViews = Depends(get_use_case_views)
    ) -> list[VistaSaldosPendientes]:
        return self._execute(use_case.get_vista_saldos_pendientes)

    def get_vista_compras_pendientes(
        self, use_case: InPortViews = Depends(get_use_case_views)
    ) -> list[VistaComprasPendientes]:
        return self._execute(use_case.get_vista_compras_pendientes)

    def get_vista_transferencias_en_transito(
        self, use_case: InPortViews = Depends(get_use_case_views)
    ) -> list[VistaTransferenciasEnTransito]:
        return self._execute(use_case.get_vista_transferencias_en_transito)

    def get_vista_devoluciones_por_producto(
        self, use_case: InPortViews = Depends(get_use_case_views)
    ) -> list[VistaDevolucionesPorProducto]:
        return self._execute(use_case.get_vista_devoluciones_por_producto)

    def get_vista_reporte_corporativo(
        self, use_case: InPortViews = Depends(get_use_case_views)
    ) -> list[VistaReporteCorporativo]:
        return self._execute(use_case.get_vista_reporte_corporativo)
