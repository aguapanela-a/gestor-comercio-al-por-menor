from decimal import Decimal

from app.services.reportes.nucleo.modelos.view_model import ViewModel


class VistaReporteCorporativo(ViewModel):
    id_sede: int
    sede: str
    tipo_sede: str
    productos_activos: int
    unidades_inventario: int
    ventas_total: Decimal
    pedidos_pendientes: int
    ordenes_compra: int
    valor_compras: Decimal
    transferencias_enviadas: int
    transferencias_recibidas: int
