import importlib
import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import Depends, HTTPException, Request
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.config import settings
from app.core.security import create_access_token, get_current_user
from app.services.identidad.dependencies import get_identity_db
from app.services.identidad.main import app as identity_app
from app.shared.api import create_service_app
from app.shared.audit import (
    AUDIT_SERVICES,
    AuditRequestMiddleware,
    AuditDeliveryError,
    _json_safe,
    registrar_evento,
    set_audit_details,
)


class FakeResult:
    def __init__(self, rowcount: int = 1) -> None:
        self.rowcount = rowcount


class FakeDatabaseSession:
    def __init__(self, rowcount: int = 1) -> None:
        self.rowcount = rowcount
        self.statements: list[tuple[str, dict | None]] = []
        self.commits = 0

    def execute(self, statement, parameters=None):
        self.statements.append((str(statement), parameters))
        return FakeResult(self.rowcount)

    def commit(self):
        self.commits += 1


class IdempotentFakeDatabaseSession(FakeDatabaseSession):
    def __init__(self) -> None:
        super().__init__()
        self.event_ids: set[str] = set()
        self.records: list[dict] = []

    def execute(self, statement, parameters=None):
        self.statements.append((str(statement), parameters))
        event_id = parameters["event_id"]
        if event_id in self.event_ids:
            return FakeResult(rowcount=0)
        self.event_ids.add(event_id)
        self.records.append(dict(parameters))
        return FakeResult(rowcount=1)


def event_payload(
    *,
    service: str = "catalogo",
    actor_id: int | None = 7,
    event_id: str | None = None,
    details: dict | None = None,
) -> dict:
    return {
        "event_id": event_id or str(uuid4()),
        "id_usuario": actor_id,
        "fecha_hora": "2026-11-25T10:30:00+00:00",
        "microservicio": service,
        "modulo": "products",
        "accion": "POST /products",
        "tipo_objeto": "catalogo.productos",
        "id_objeto": '{"id_producto":42}',
        "resultado": "SUCCESS",
        "metodo_http": "POST",
        "ruta": "/products",
        "direccion_ip": "127.0.0.1",
        "correlation_id": str(uuid4()),
        "detalles": details or {"operacion": "crear"},
    }


def service_token(event: dict) -> str:
    return create_access_token({
        "sub": f"service:{event['microservicio']}",
        "token_use": "audit_ingest",
        "service": event["microservicio"],
        "actor_id": event["id_usuario"],
        "event_id": event["event_id"],
    })


def test_legacy_outbox_migration_is_retired_and_cleanup_preserves_pending_data() -> None:
    backend_root = Path(__file__).parents[1]
    cleanup = (backend_root / "migrations" / "004_remove_audit_outbox.sql").read_text(
        encoding="utf-8"
    )

    assert not (backend_root / "migrations" / "002_audit_outbox.sql").exists()
    assert not (backend_root / "app" / "shared" / "audit_outbox.py").exists()
    assert "DROP TRIGGER" in cleanup
    assert "DROP FUNCTION IF EXISTS audit_local.capture_row_change()" in cleanup
    assert "IF pending_count = 0 THEN" in cleanup
    assert "DROP TABLE audit_local.outbox" in cleanup
    assert "identidad.auditoria_accesos" not in cleanup


def test_middleware_audits_success_and_denial_with_validated_actor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "jwt_secret_key", "audit-pipeline-test-key")
    monkeypatch.setattr(settings, "audit_capture_enabled", True)
    persisted: list[dict] = []
    monkeypatch.setattr("app.shared.audit.registrar_evento", persisted.append)
    app = create_service_app("catalogo", "Auditoría de prueba")

    def success(request: Request, product_id: int):
        set_audit_details(
            request,
            action="Producto actualizado",
            object_type="catalogo.productos",
            object_id=product_id,
            before={
                "nombre": "Anterior",
                "password_hash": "no-debe-registrarse",
                "nombre_cliente": "Cliente Ejemplo",
            },
            after={
                "nombre": "Nuevo",
                "password_hash": "no-debe-registrarse",
                "nombre_cliente": "Cliente Ejemplo",
            },
        )
        return {"product_id": product_id}

    def denied():
        raise HTTPException(status_code=403, detail="No autorizado")

    app.add_api_route("/products/{product_id}", success, methods=["PATCH"])
    app.add_api_route("/denied", denied, methods=["GET"])
    token = create_access_token({"sub": "7"})
    correlation_id = str(uuid4())

    with TestClient(app) as client:
        response = client.patch(
            "/products/42",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Correlation-ID": correlation_id,
            },
        )
        denied_response = client.get("/denied")

    assert response.status_code == 200
    assert response.headers["X-Audit-Status"] == "persisted"
    assert denied_response.status_code == 403
    assert len(persisted) == 2
    assert persisted[0]["id_usuario"] == 7
    assert persisted[0]["resultado"] == "SUCCESS"
    assert persisted[0]["correlation_id"] == correlation_id
    assert persisted[0]["detalles"]["cambios"] == {
        "antes": {"nombre": "Anterior"},
        "despues": {"nombre": "Nuevo"},
    }
    assert persisted[1]["resultado"] == "DENIED"


def test_json_safe_sanitizes_sensitive_fields_in_nested_pydantic_models() -> None:
    class NestedDetails(BaseModel):
        id_registro: int
        password: str
        email: str
        documento: str
        telefono: str

    class AuditDetails(BaseModel):
        id_usuario: int
        nested: list[NestedDetails]

    safe_details = _json_safe(
        AuditDetails(
            id_usuario=17,
            nested=[
                NestedDetails(
                    id_registro=42,
                    password="do-not-store",
                    email="private@example.test",
                    documento="DOC-123",
                    telefono="555-0100",
                )
            ],
        )
    )

    assert safe_details == {
        "id_usuario": 17,
        "nested": [{"id_registro": 42}],
    }


def test_json_safe_stops_recursive_model_dump_and_container_cycles() -> None:
    class RecursiveDump:
        def model_dump(self, *, mode: str):
            return {"self": self}

    cyclic_list: list[object] = []
    cyclic_list.append(cyclic_list)

    assert _json_safe(RecursiveDump()) == {"self": None}
    assert _json_safe(cyclic_list) == [None]


def test_all_seven_services_use_the_shared_audit_middleware(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "audit_capture_enabled", True)
    persisted: list[dict] = []
    monkeypatch.setattr("app.shared.audit.registrar_evento", persisted.append)

    for service in AUDIT_SERVICES:
        app = create_service_app(service, f"API {service}")
        app.add_api_route("/probe", lambda: {"ok": True})
        with TestClient(app) as client:
            response = client.get("/probe")
        assert response.status_code == 200

    assert {event["microservicio"] for event in persisted} == set(AUDIT_SERVICES)


@pytest.mark.parametrize(
    ("service", "module_name"),
    [
        ("catalogo", "app.services.catalogo.main"),
        ("organizacion", "app.services.organizacion.main"),
        ("compras", "app.services.compras.main"),
        ("inventarios", "app.services.inventarios.main"),
        ("ventas", "app.services.ventas.main"),
        ("identidad", "app.services.identidad.main"),
        ("reportes", "app.services.reportes.main"),
    ],
)
def test_each_service_entrypoint_registers_one_named_audit_middleware_and_router(
    service: str,
    module_name: str,
) -> None:
    service_app = importlib.import_module(module_name).app
    audit_middlewares = [
        middleware
        for middleware in service_app.user_middleware
        if middleware.cls is AuditRequestMiddleware
    ]

    assert len(audit_middlewares) == 1
    assert audit_middlewares[0].kwargs["service"] == service
    assert any(
        route.path not in {"/health", "/health/database"}
        for route in service_app.routes
        if hasattr(route, "path")
    )


def test_middleware_audits_unhandled_exceptions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "audit_capture_enabled", True)
    persisted: list[dict] = []
    monkeypatch.setattr("app.shared.audit.registrar_evento", persisted.append)
    app = create_service_app("inventarios", "Auditoría de prueba")

    def fail():
        raise RuntimeError("error de prueba")

    app.add_api_route("/stock/failure", fail, methods=["POST"])
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/stock/failure")

    assert response.status_code == 500
    assert len(persisted) == 1
    assert persisted[0]["resultado"] == "FAILURE"
    assert persisted[0]["ruta"] == "/stock/failure"


def test_committed_mutation_reports_audit_delivery_failure_without_retrying_operation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "audit_capture_enabled", True)
    operations: list[str] = []
    delivery_attempts: list[dict] = []

    def fail_delivery(event):
        delivery_attempts.append(event)
        raise AuditDeliveryError("Identity unavailable")

    monkeypatch.setattr("app.shared.audit.registrar_evento", fail_delivery)
    app = create_service_app("catalogo", "Auditoría de prueba")

    def create_product():
        operations.append("committed")
        return {"id_producto": 4}

    app.add_api_route("/products", create_product, methods=["POST"])
    with TestClient(app) as client:
        response = client.post("/products")

    assert response.status_code == 503
    assert response.json() == {
        "detail": "La operación fue confirmada, pero no se pudo persistir su auditoría.",
        "business_operation_committed": True,
        "audit_persisted": False,
        "retryable": False,
        "correlation_id": response.json()["correlation_id"],
    }
    assert response.headers["X-Business-Operation"] == "committed"
    assert operations == ["committed"]
    assert len(delivery_attempts) == 1


def test_noncritical_read_exposes_audit_failure_without_hiding_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "audit_capture_enabled", True)

    def fail_delivery(_event):
        raise AuditDeliveryError("Identity unavailable")

    monkeypatch.setattr("app.shared.audit.registrar_evento", fail_delivery)
    app = create_service_app("reportes", "Auditoría de prueba")
    app.add_api_route("/vistas", lambda: [{"vista": "ventas"}], methods=["GET"])

    with TestClient(app) as client:
        response = client.get("/vistas")

    assert response.status_code == 200
    assert response.json() == [{"vista": "ventas"}]
    assert response.headers["X-Audit-Status"] == "failed"
    assert response.headers["X-Audit-Error"] == "identity-unavailable"


def test_signed_internal_service_hop_is_not_a_duplicate_audit_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "jwt_secret_key", "audit-pipeline-test-key")
    monkeypatch.setattr(settings, "audit_capture_enabled", True)
    persisted: list[dict] = []
    monkeypatch.setattr("app.shared.audit.registrar_evento", persisted.append)
    app = create_service_app("catalogo", "Auditoría de prueba")
    app.add_api_route("/products/{product_id}", lambda product_id: {"id": product_id})

    def protected(current_user=Depends(get_current_user)):
        return {"id_usuario": current_user["sub"]}

    app.add_api_route("/protected", protected)
    correlation_id = str(uuid4())
    delegation = create_access_token({
        "sub": "service:compras",
        "token_use": "audit_delegation",
        "service": "compras",
        "correlation_id": correlation_id,
        "destination": "catalogo",
    })
    user_token = create_access_token({"sub": "7"})

    with TestClient(app) as client:
        response = client.get(
            "/products/42",
            headers={
                "Authorization": f"Bearer {user_token}",
                "X-Correlation-ID": correlation_id,
                "X-Audit-Delegation": delegation,
            },
        )
        service_token_response = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {delegation}"},
        )

    assert response.status_code == 200
    assert service_token_response.status_code == 401
    assert len(persisted) == 1
    assert persisted[0]["resultado"] == "DENIED"


def test_registrar_evento_sends_signed_event_to_identity_with_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "jwt_secret_key", "audit-pipeline-test-key")
    monkeypatch.setattr(
        settings,
        "identidad_service_url",
        "https://identity.example.test/",
    )
    event = event_payload()
    requests: list[tuple[str, dict, dict, float]] = []

    class Response:
        status_code = 202

    class Client:
        def __init__(self, *, timeout):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def post(self, url, *, json, headers):
            requests.append((url, json, headers, self.timeout))
            return Response()

    monkeypatch.setattr("app.shared.audit.httpx.Client", Client)
    registrar_evento(event)

    assert len(requests) == 1
    url, payload, headers, timeout = requests[0]
    assert url.endswith("/internal/audit/events")
    assert payload == event
    assert headers["Authorization"].startswith("Bearer ")
    assert timeout == settings.service_http_timeout_seconds


def test_identity_accepts_signed_service_event_idempotently(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "jwt_secret_key", "audit-pipeline-test-key")
    event = event_payload()
    db = IdempotentFakeDatabaseSession()
    recursive_events: list[dict] = []
    monkeypatch.setattr("app.shared.audit.registrar_evento", recursive_events.append)
    monkeypatch.setitem(identity_app.dependency_overrides, get_identity_db, lambda: db)

    with TestClient(identity_app) as client:
        response = client.post(
            "/internal/audit/events",
            json=event,
            headers={"Authorization": f"Bearer {service_token(event)}"},
        )
        duplicate_response = client.post(
            "/internal/audit/events",
            json=event,
            headers={"Authorization": f"Bearer {service_token(event)}"},
        )

    assert response.status_code == 202
    assert response.json() == {"event_id": event["event_id"], "duplicate": False}
    assert duplicate_response.status_code == 202
    assert duplicate_response.json() == {"event_id": event["event_id"], "duplicate": True}
    statement, _ = db.statements[0]
    assert "INSERT INTO identidad.auditoria_accesos" in statement
    assert "ON CONFLICT (event_id) DO NOTHING" in statement
    assert len(db.records) == 1
    parameters = db.records[0]
    assert parameters == {
        "event_id": event["event_id"],
        "id_usuario": 7,
        "fecha_hora": datetime(2026, 11, 25, 10, 30),
        "accion": "POST /products",
        "objeto_consultado": "catalogo.productos",
        "microservicio": "catalogo",
        "modulo": "products",
        "tipo_objeto": "catalogo.productos",
        "id_objeto": '{"id_producto":42}',
        "resultado": "SUCCESS",
        "metodo_http": "POST",
        "ruta": "/products",
        "direccion_ip": "127.0.0.1",
        "correlation_id": event["correlation_id"],
        "detalles": json.dumps(event["detalles"], ensure_ascii=False),
    }
    assert db.commits == 2
    assert recursive_events == []


def test_identity_rejects_user_tokens_and_service_actor_mismatches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "jwt_secret_key", "audit-pipeline-test-key")
    event = event_payload()
    db = FakeDatabaseSession()
    monkeypatch.setitem(identity_app.dependency_overrides, get_identity_db, lambda: db)

    with TestClient(identity_app) as client:
        user_token_response = client.post(
            "/internal/audit/events",
            json=event,
            headers={"Authorization": f"Bearer {create_access_token({'sub': '7'})}"},
        )
        mismatch_response = client.post(
            "/internal/audit/events",
            json={**event, "id_usuario": 8},
            headers={"Authorization": f"Bearer {service_token(event)}"},
        )

    assert user_token_response.status_code == 401
    assert mismatch_response.status_code == 403
    assert db.statements == []


@pytest.mark.parametrize(
    "sensitive_key",
    ["password_hash", "correo", "nombre_cliente", "fecha_nacimiento"],
)
def test_identity_rejects_sensitive_event_details(
    monkeypatch: pytest.MonkeyPatch,
    sensitive_key: str,
) -> None:
    monkeypatch.setattr(settings, "jwt_secret_key", "audit-pipeline-test-key")
    event = event_payload(details={"changes": {sensitive_key: "do-not-store"}})
    db = FakeDatabaseSession()
    monkeypatch.setitem(identity_app.dependency_overrides, get_identity_db, lambda: db)

    with TestClient(identity_app) as client:
        response = client.post(
            "/internal/audit/events",
            json=event,
            headers={"Authorization": f"Bearer {service_token(event)}"},
        )

    assert response.status_code == 422
    assert db.statements == []


