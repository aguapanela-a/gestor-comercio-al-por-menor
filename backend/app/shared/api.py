from fastapi import FastAPI, HTTPException, status

from app.core.database import SERVICE_DATABASE_SETTINGS
from app.core.health import check_database_connection


def create_service_app(service: str, title: str) -> FastAPI:
    if service not in SERVICE_DATABASE_SETTINGS:
        raise ValueError(f"Servicio sin base de datos configurada: {service}")

    app = FastAPI(title=title, version="1.0.0")

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
