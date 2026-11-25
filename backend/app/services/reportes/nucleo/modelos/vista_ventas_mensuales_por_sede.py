from datetime import date
from decimal import Decimal

from app.services.reportes.nucleo.modelos.view_model import ViewModel


class VistaVentasMensualesPorSede(ViewModel):
    id_sede: int
    sede: str
    mes: date
    pedidos: int
    total_vendido: Decimal
    total_mes_anterior: Decimal | None
    variacion: Decimal | None
    variacion_pct: Decimal | None
