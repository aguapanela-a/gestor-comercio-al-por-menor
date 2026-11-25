from decimal import Decimal

from app.services.reportes.nucleo.modelos.view_model import ViewModel


class VistaDevolucionesPorProducto(ViewModel):
    id_producto: int
    sku: str
    producto: str
    categoria: str
    cantidad_vendida: int
    cantidad_devuelta: int
    porcentaje_devolucion: Decimal | None
