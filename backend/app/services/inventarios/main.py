from app.shared.api import create_service_app
from app.services.inventarios.router import router

app = create_service_app("inventarios", "API de Inventarios")
app.include_router(router)
