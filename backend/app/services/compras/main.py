from app.shared.api import create_service_app
from app.services.compras.router import router

app = create_service_app("compras", "API de Compras")
app.include_router(router)
