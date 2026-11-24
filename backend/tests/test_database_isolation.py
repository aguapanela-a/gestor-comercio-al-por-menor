import pytest

import app.core.database as database
from app.core.config import settings


@pytest.mark.parametrize(
    ("service", "database_name"),
    [
        ("identidad", "identidad_db"),
        ("catalogo", "catalogo_db"),
        ("organizacion", "organizacion_db"),
        ("compras", "compras_db"),
        ("inventarios", "inventarios_db"),
        ("ventas", "ventas_db"),
        ("reportes", "reportes_db"),
    ],
)
def test_engine_is_created_only_for_requested_service(
    monkeypatch: pytest.MonkeyPatch,
    service: str,
    database_name: str,
) -> None:
    monkeypatch.setattr(database, "ENGINES", {})
    monkeypatch.setattr(database, "SESSION_FACTORIES", {})

    for configured_service, setting_names in database.SERVICE_DATABASE_SETTINGS.items():
        if configured_service == service:
            configured_values = (
                "localhost",
                database_name,
                "test_user",
                "test_password",
            )
            for name, value in zip(
                setting_names,
                configured_values,
                strict=True,
            ):
                monkeypatch.setattr(settings, name, value)
        else:
            for name in setting_names:
                monkeypatch.setattr(settings, name, None)

    engine = database.get_engine(service)

    assert engine.url.database == database_name
    assert set(database.ENGINES) == {service}
    engine.dispose()
