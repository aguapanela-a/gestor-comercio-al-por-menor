from app.services.reportes.infraestructura.adaptadores_salida.base_view_adapter import (
    BaseViewAdapter,
)


class VistaComprasPendientes(BaseViewAdapter):
    entity_name = "vista_compras_pendientes"
    query = "SELECT * FROM reportes.vista_compras_pendientes;"
