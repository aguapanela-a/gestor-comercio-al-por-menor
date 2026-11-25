from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_catalogo_host: str | None = None
    database_catalogo_name: str | None = None
    database_catalogo_user: str | None = None
    database_catalogo_password: str | None = None

    database_organizacion_host: str | None = None
    database_organizacion_name: str | None = None
    database_organizacion_user: str | None = None
    database_organizacion_password: str | None = None

    database_compras_host: str | None = None
    database_compras_name: str | None = None
    database_compras_user: str | None = None
    database_compras_password: str | None = None

    database_inventarios_host: str | None = None
    database_inventarios_name: str | None = None
    database_inventarios_user: str | None = None
    database_inventarios_password: str | None = None

    database_ventas_host: str | None = None
    database_ventas_name: str | None = None
    database_ventas_user: str | None = None
    database_ventas_password: str | None = None

    database_identidad_host: str | None = None
    database_identidad_name: str | None = None
    database_identidad_user: str | None = None
    database_identidad_password: str | None = None

    database_reportes_host: str | None = None
    database_reportes_name: str | None = None
    database_reportes_user: str | None = None
    database_reportes_password: str | None = None

    database_port: int = 5432
    database_sslmode: str = "require"
    jwt_secret_key: str | None = None
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    identidad_service_url: str = "http://127.0.0.1:8001"
    catalogo_service_url: str = "http://127.0.0.1:8002"
    organizacion_service_url: str = "http://127.0.0.1:8003"
    compras_service_url: str = "http://127.0.0.1:8004"
    inventarios_service_url: str = "http://127.0.0.1:8005"
    ventas_service_url: str = "http://127.0.0.1:8006"
    service_http_timeout_seconds: float = Field(default=3.0, gt=0)
    cors_allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"


settings = Settings()
