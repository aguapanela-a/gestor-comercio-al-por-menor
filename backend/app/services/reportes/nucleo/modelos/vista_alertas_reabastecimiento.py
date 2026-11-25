from app.services.reportes.nucleo.modelos.view_model import ViewModel


class VistaAlertasReabastecimiento(ViewModel):
    id_sede: int
    sede: str
    id_almacen: int
    almacen: str
    id_producto: int
    sku: str
    producto: str
    existencia_actual: int
    stock_minimo: int
    faltante: int
    nivel_alerta: str
