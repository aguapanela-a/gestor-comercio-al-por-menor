from app.services.reportes.infraestructura.adaptadores_salida.base_view_adapter import (
    BaseViewAdapter,
)


class VistaDevolucionesPorProducto(BaseViewAdapter):
    entity_name = "vista_devoluciones_por_producto"
    query = "SELECT * FROM reportes.vista_devoluciones_por_producto;"
