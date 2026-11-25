from app.services.reportes.infraestructura.adaptadores_salida.base_view_adapter import (
    BaseViewAdapter,
)


class VistaReporteCorporativo(BaseViewAdapter):
    entity_name = "vista_reporte_corporativo"
    query = "SELECT * FROM reportes.vista_reporte_corporativo;"
