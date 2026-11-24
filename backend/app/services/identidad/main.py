
from app.shared.api import create_service_app
from app.services.identidad.router import router

app = create_service_app("identidad", "API de Identidad")
app.include_router(router)
