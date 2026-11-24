from app.shared.api import create_service_app
from app.services.ventas.router import router

app = create_service_app("ventas", "API de Ventas")
app.include_router(router)
