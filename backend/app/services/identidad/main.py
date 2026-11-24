
from app.shared.api import create_service_app
from app.services.identidad.router import router
from app.services.identidad.employees import router as employees_router
from app.services.identidad.users import accounts_router, router as users_router

app = create_service_app("identidad", "API de Identidad")
app.include_router(router)
app.include_router(users_router)
app.include_router(employees_router)
app.include_router(accounts_router)
