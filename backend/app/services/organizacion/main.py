from app.shared.api import create_service_app
from app.services.organizacion.router import router

app = create_service_app("organizacion", "API de Organización")
app.include_router(router)
