from app.services.reportes.infraestructura.adaptadores_salida.base_view_adapter import (
    BaseViewAdapter,
)


class VistaVentasMensualesPorSede(BaseViewAdapter):
    entity_name = "vista_ventas_mensuales_por_sede"
    query = "SELECT * FROM reportes.vista_ventas_mensuales_por_sede;"
