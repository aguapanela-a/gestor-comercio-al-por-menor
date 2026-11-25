from datetime import date, datetime
from decimal import Decimal

from app.services.reportes.nucleo.modelos.view_model import ViewModel


class VistaSaldosPendientes(ViewModel):
    id_pedido: int
    id_sede: int
    sede: str
    id_cliente: int
    cliente: str
    fecha_pedido: date | datetime
    total_registrado: Decimal
    pagos_confirmados: Decimal
    saldo_pendiente: Decimal
