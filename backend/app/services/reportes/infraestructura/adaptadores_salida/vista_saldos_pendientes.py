from app.services.reportes.infraestructura.adaptadores_salida.base_view_adapter import (
    BaseViewAdapter,
)


class VistaSaldosPendientes(BaseViewAdapter):
    entity_name = "vista_saldos_pendientes"
    query = "SELECT * FROM reportes.vista_saldos_pendientes;"
