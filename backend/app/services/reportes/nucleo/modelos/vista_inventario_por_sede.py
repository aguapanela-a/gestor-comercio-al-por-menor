from decimal import Decimal

from app.services.reportes.nucleo.modelos.view_model import ViewModel


class VistaInventarioPorSede(ViewModel):
    id_sede: int
    sede: str
    id_almacen: int
    almacen: str
    id_producto: int
    sku: str
    producto: str
    categoria: str
    existencia_actual: int
    stock_minimo: int
    precio_lista: Decimal
    valorizacion_estimada: Decimal
