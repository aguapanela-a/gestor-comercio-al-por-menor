from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import SERVICE_DATABASE_SETTINGS, get_engine
from app.shared.exceptions import DatabaseConfigurationError


def check_database_connection(service: str) -> dict[str, str | bool | None]:
    if service not in SERVICE_DATABASE_SETTINGS:
        return {"service": service, "connected": False, "error": "Servicio desconocido"}

    try:
        with get_engine(service).connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"service": service, "connected": True, "error": None}
    except DatabaseConfigurationError as exc:
        return {"service": service, "connected": False, "error": str(exc)}
    except SQLAlchemyError:
        return {
            "service": service,
            "connected": False,
            "error": "No fue posible conectar con la base de datos configurada",
        }


def check_all_databases() -> list[dict[str, str | bool | None]]:
    return [
        check_database_connection(service)
        for service in SERVICE_DATABASE_SETTINGS
    ]
