from datetime import date, datetime
from decimal import Decimal

from app.services.reportes.nucleo.modelos.view_model import ViewModel


class VistaComprasPendientes(ViewModel):
    id_orden_compra: int
    proveedor: str
    id_almacen_destino: int
    almacen_destino: str
    fecha_orden: date | datetime
    fecha_estimada: date | datetime | None
    estado_orden: str
    id_producto: int
    producto: str
    cantidad_solicitada: int
    cantidad_recibida: int
    cantidad_pendiente: int
