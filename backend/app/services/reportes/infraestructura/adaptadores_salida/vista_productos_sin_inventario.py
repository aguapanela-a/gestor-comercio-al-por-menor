from app.services.reportes.infraestructura.adaptadores_salida.base_view_adapter import (
    BaseViewAdapter,
)


class VistaProductosSinInventario(BaseViewAdapter):
    entity_name = "vista_productos_sin_inventario"
    query = "SELECT * FROM reportes.vista_productos_sin_inventario;"
