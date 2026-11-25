from app.services.reportes.infraestructura.adaptadores_salida.base_view_adapter import (
    BaseViewAdapter,
)


class VistaTransferenciasEnTransito(BaseViewAdapter):
    entity_name = "vista_transferencias_en_transito"
    query = "SELECT * FROM reportes.vista_transferencias_en_transito;"
