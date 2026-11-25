from datetime import date, datetime
from decimal import Decimal

from app.services.reportes.nucleo.modelos.view_model import ViewModel


class VistaPedidosPendientes(ViewModel):
    id_pedido: int
    id_sede: int
    sede: str
    id_almacen: int
    almacen: str
    id_cliente: int
    cliente: str
    id_empleado: int | None
    vendedor: str | None
    fecha_pedido: date | datetime
    dias_antiguedad: int
    total_registrado: Decimal
