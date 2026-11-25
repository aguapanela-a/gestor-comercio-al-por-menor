from collections.abc import Generator

import psycopg
from psycopg import Connection

from app.core.config import settings
from app.shared.exceptions import DatabaseConfigurationError


def get_connection() -> Generator[Connection[dict[str, object]], None, None]:
    required_settings = {
        "DATABASE_REPORTES_HOST": settings.database_reportes_host,
        "DATABASE_REPORTES_NAME": settings.database_reportes_name,
        "DATABASE_REPORTES_USER": settings.database_reportes_user,
        "DATABASE_REPORTES_PASSWORD": settings.database_reportes_password,
    }
    missing = [name for name, value in required_settings.items() if not value]
    if missing:
        raise DatabaseConfigurationError(
            f"Falta configuración de base de datos para reportes: {', '.join(missing)}"
        )

    connection = psycopg.connect(
        host=settings.database_reportes_host,
        dbname=settings.database_reportes_name,
        user=settings.database_reportes_user,
        password=settings.database_reportes_password,
        port=settings.database_port,
        sslmode=settings.database_sslmode,
        row_factory=psycopg.rows.dict_row,
    )
    try:
        yield connection
    finally:
        connection.close()
