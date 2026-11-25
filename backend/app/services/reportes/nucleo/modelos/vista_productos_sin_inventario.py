from app.services.reportes.nucleo.modelos.view_model import ViewModel


class VistaProductosSinInventario(ViewModel):
    id_sede: int
    sede: str
    id_producto: int
    sku: str
    producto: str
