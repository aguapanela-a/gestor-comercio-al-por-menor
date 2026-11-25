from abc import ABC, abstractmethod

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


class InPortViews(ABC):
    @abstractmethod
    def get_vista_inventario_por_sede(self) -> list[VistaInventarioPorSede]:
        raise NotImplementedError

    @abstractmethod
    def get_vista_alertas_reabastecimiento(self) -> list[VistaAlertasReabastecimiento]:
        raise NotImplementedError

    @abstractmethod
    def get_vista_productos_sin_inventario(self) -> list[VistaProductosSinInventario]:
        raise NotImplementedError

    @abstractmethod
    def get_vista_ventas_mensuales_por_sede(self) -> list[VistaVentasMensualesPorSede]:
        raise NotImplementedError

    @abstractmethod
    def get_vista_pedidos_pendientes(self) -> list[VistaPedidosPendientes]:
        raise NotImplementedError

    @abstractmethod
    def get_vista_saldos_pendientes(self) -> list[VistaSaldosPendientes]:
        raise NotImplementedError

    @abstractmethod
    def get_vista_compras_pendientes(self) -> list[VistaComprasPendientes]:
        raise NotImplementedError

    @abstractmethod
    def get_vista_transferencias_en_transito(self) -> list[VistaTransferenciasEnTransito]:
        raise NotImplementedError

    @abstractmethod
    def get_vista_devoluciones_por_producto(self) -> list[VistaDevolucionesPorProducto]:
        raise NotImplementedError

    @abstractmethod
    def get_vista_reporte_corporativo(self) -> list[VistaReporteCorporativo]:
        raise NotImplementedError
