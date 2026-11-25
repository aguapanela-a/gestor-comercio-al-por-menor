from app.services.reportes.infraestructura.adaptadores_salida.base_view_adapter import (
    BaseViewAdapter,
)


class VistaPedidosPendientes(BaseViewAdapter):
    entity_name = "vista_pedidos_pendientes"
    query = "SELECT * FROM reportes.vista_pedidos_pendientes;"
