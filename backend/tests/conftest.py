from collections.abc import Callable

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import settings


@pytest.fixture(autouse=True)
def disable_external_audit_services(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "audit_capture_enabled", False)


@pytest.fixture
def assert_health_endpoints(
    monkeypatch: pytest.MonkeyPatch,
) -> Callable[[FastAPI, str], None]:
    def assert_endpoints(app: FastAPI, service: str) -> None:
        monkeypatch.setattr(
            "app.shared.api.check_database_connection",
            lambda name: {"service": name, "connected": True, "error": None},
        )
        with TestClient(app) as client:
            response = client.get("/health")
            assert response.status_code == 200
            assert response.json() == {"service": service, "status": "running"}

            database_response = client.get("/health/database")
            assert database_response.status_code == 200
            assert database_response.json() == {
                "service": service,
                "database": "connected",
            }

    return assert_endpoints
