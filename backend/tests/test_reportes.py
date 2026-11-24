from fastapi.testclient import TestClient

from app.services.reportes.main import app


def test_reportes_health(assert_health_endpoints) -> None:
    assert_health_endpoints(app, "reportes")


def test_database_health_reports_unavailable_without_connecting(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "app.shared.api.check_database_connection",
        lambda _service: {
            "service": "reportes",
            "connected": False,
            "error": "Falta configuración de prueba",
        },
    )
    with TestClient(app) as client:
        response = client.get("/health/database")

    assert response.status_code == 503
    assert response.json()["detail"]["database"] == "disconnected"
