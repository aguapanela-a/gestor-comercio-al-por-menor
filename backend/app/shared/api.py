from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import SERVICE_DATABASE_SETTINGS
from app.core.health import check_database_connection
from app.shared.audit import AuditRequestMiddleware


def create_service_app(service: str, title: str) -> FastAPI:
    if service not in SERVICE_DATABASE_SETTINGS:
        raise ValueError(f"Servicio sin base de datos configurada: {service}")

    app = FastAPI(title=title, version="1.0.0")
    app.add_middleware(AuditRequestMiddleware, service=service)

    allowed_origins = [
        origin.strip()
        for origin in settings.cors_allowed_origins.split(",")
        if origin.strip()
    ]
    if allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=True,
            allow_methods=['*'],
            allow_headers=["*"],
            expose_headers=["X-Audit-Status", "X-Audit-Error", "X-Correlation-ID"],
        )

    @app.get("/health")
    def health():
        return {"service": service, "status": "running"}

    @app.get("/health/database")
    def database_health():
        result = check_database_connection(service)
        if not result["connected"]:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "service": service,
                    "database": "disconnected",
                    "error": result["error"],
                },
            )
        return {"service": service, "database": "connected"}

    return app
