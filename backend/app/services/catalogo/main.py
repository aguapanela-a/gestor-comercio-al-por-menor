from app.shared.api import create_service_app
from app.services.catalogo.router import router

app = create_service_app("catalogo", "API de Catálogo")
app.include_router(router)
