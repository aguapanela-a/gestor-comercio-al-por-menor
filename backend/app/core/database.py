from collections.abc import Generator

from sqlalchemy import Engine, URL, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.shared.exceptions import DatabaseConfigurationError

SERVICE_DATABASE_SETTINGS = {
    "catalogo": (
        "database_catalogo_host",
        "database_catalogo_name",
        "database_catalogo_user",
        "database_catalogo_password",
    ),
    "organizacion": (
        "database_organizacion_host",
        "database_organizacion_name",
        "database_organizacion_user",
        "database_organizacion_password",
    ),
    "compras": (
        "database_compras_host",
        "database_compras_name",
        "database_compras_user",
        "database_compras_password",
    ),
    "inventarios": (
        "database_inventarios_host",
        "database_inventarios_name",
        "database_inventarios_user",
        "database_inventarios_password",
    ),
    "ventas": (
        "database_ventas_host",
        "database_ventas_name",
        "database_ventas_user",
        "database_ventas_password",
    ),
    "identidad": (
        "database_identidad_host",
        "database_identidad_name",
        "database_identidad_user",
        "database_identidad_password",
    ),
    "reportes": (
        "database_reportes_host",
        "database_reportes_name",
        "database_reportes_user",
        "database_reportes_password",
    ),
}

ENGINES: dict[str, Engine] = {}
SESSION_FACTORIES: dict[str, sessionmaker[Session]] = {}


def get_engine(service: str) -> Engine:
    if service not in SERVICE_DATABASE_SETTINGS:
        raise DatabaseConfigurationError(f"Servicio de base de datos desconocido: {service}")

    if service not in ENGINES:
        setting_names = SERVICE_DATABASE_SETTINGS[service]
        values = [getattr(settings, name) for name in setting_names]
        if any(not value for value in values):
            missing = [
                name.upper()
                for name, value in zip(setting_names, values, strict=True)
                if not value
            ]
            raise DatabaseConfigurationError(
                f"Falta configuración de base de datos para {service}: {', '.join(missing)}"
            )

        host, name, user, password = values
        url = URL.create(
            "postgresql+psycopg",
            username=user,
            password=password,
            host=host,
            port=settings.database_port,
            database=name,
        )
        ENGINES[service] = create_engine(
            url,
            connect_args={"sslmode": settings.database_sslmode},
            pool_pre_ping=True,
            hide_parameters=True,
        )
        SESSION_FACTORIES[service] = sessionmaker(
            bind=ENGINES[service],
            autoflush=False,
            autocommit=False,
        )

    return ENGINES[service]


def get_db(service: str) -> Generator[Session, None, None]:
    get_engine(service)
    db = SESSION_FACTORIES[service]()
    try:
        yield db
    finally:
        db.close()
