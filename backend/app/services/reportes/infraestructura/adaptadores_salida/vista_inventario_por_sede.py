from app.services.reportes.infraestructura.adaptadores_salida.base_view_adapter import (
    BaseViewAdapter,
)


class VistaInventarioPorSede(BaseViewAdapter):
    entity_name = "vista_inventario_por_sede"
    query = "SELECT * FROM reportes.vista_inventario_por_sede;"
