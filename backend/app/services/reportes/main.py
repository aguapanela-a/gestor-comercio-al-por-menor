from app.shared.api import create_service_app
from app.services.reportes.router import router

app = create_service_app("reportes", "API de Reportes")
app.include_router(router)
