from app.services.reportes.infraestructura.adaptadores_salida.base_view_adapter import (
    BaseViewAdapter,
)


class VistaAlertasReabastecimiento(BaseViewAdapter):
    entity_name = "vista_alertas_reabastecimiento"
    query = "SELECT * FROM reportes.vista_alertas_reabastecimiento;"
