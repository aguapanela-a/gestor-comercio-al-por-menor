from datetime import date, datetime

from app.services.reportes.nucleo.modelos.view_model import ViewModel


class VistaTransferenciasEnTransito(ViewModel):
    id_transferencia: int
    id_almacen_origen: int
    almacen_origen: str
    sede_origen: str
    id_almacen_destino: int
    almacen_destino: str
    sede_destino: str
    fecha_despacho: date | datetime
    dias_transcurridos: int
    id_producto: int
    producto: str
    cantidad_enviada: int
