from app.services.reportes.aplicacion.puertos_entrada import InPortViews
from app.services.reportes.aplicacion.puertos_salida import OutPortViews
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


class UseCaseViews(InPortViews):
    def __init__(self, out_port: OutPortViews) -> None:
        self._out_port = out_port

    def get_vista_inventario_por_sede(self) -> list[VistaInventarioPorSede]:
        return [
            VistaInventarioPorSede(row)
            for row in self._out_port.getView("vista_inventario_por_sede")
        ]

    def get_vista_alertas_reabastecimiento(self) -> list[VistaAlertasReabastecimiento]:
        return [
            VistaAlertasReabastecimiento(row)
            for row in self._out_port.getView("vista_alertas_reabastecimiento")
        ]

    def get_vista_productos_sin_inventario(self) -> list[VistaProductosSinInventario]:
        return [
            VistaProductosSinInventario(row)
            for row in self._out_port.getView("vista_productos_sin_inventario")
        ]

    def get_vista_ventas_mensuales_por_sede(self) -> list[VistaVentasMensualesPorSede]:
        return [
            VistaVentasMensualesPorSede(row)
            for row in self._out_port.getView("vista_ventas_mensuales_por_sede")
        ]

    def get_vista_pedidos_pendientes(self) -> list[VistaPedidosPendientes]:
        return [
            VistaPedidosPendientes(row)
            for row in self._out_port.getView("vista_pedidos_pendientes")
        ]

    def get_vista_saldos_pendientes(self) -> list[VistaSaldosPendientes]:
        return [
            VistaSaldosPendientes(row)
            for row in self._out_port.getView("vista_saldos_pendientes")
        ]

    def get_vista_compras_pendientes(self) -> list[VistaComprasPendientes]:
        return [
            VistaComprasPendientes(row)
            for row in self._out_port.getView("vista_compras_pendientes")
        ]

    def get_vista_transferencias_en_transito(self) -> list[VistaTransferenciasEnTransito]:
        return [
            VistaTransferenciasEnTransito(row)
            for row in self._out_port.getView("vista_transferencias_en_transito")
        ]

    def get_vista_devoluciones_por_producto(self) -> list[VistaDevolucionesPorProducto]:
        return [
            VistaDevolucionesPorProducto(row)
            for row in self._out_port.getView("vista_devoluciones_por_producto")
        ]

    def get_vista_reporte_corporativo(self) -> list[VistaReporteCorporativo]:
        return [
            VistaReporteCorporativo(row)
            for row in self._out_port.getView("vista_reporte_corporativo")
        ]
