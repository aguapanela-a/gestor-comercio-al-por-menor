from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.services.identidad.dependencies import get_identity_db
from app.services.identidad.main import app


class FakeResult:
    def __init__(self, row=None, rows=None, rowcount=0) -> None:
        self.row = row
        self.rows = rows if rows is not None else ([row] if row is not None else [])
        self.rowcount = rowcount

    def mappings(self):
        return self

    def all(self):
        return self.rows

    def first(self):
        return self.rows[0] if self.rows else None

    def one(self):
        return self.rows[0]


class FakeDatabaseSession:
    def __init__(self, *results: FakeResult) -> None:
        self.results = list(results)
        self.statements: list[tuple[str, dict | None]] = []
        self.commits = 0
        self.rollbacks = 0

    def execute(self, statement, parameters=None):
        self.statements.append((str(statement), parameters))
        if self.results:
            return self.results.pop(0)
        return FakeResult()

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


@contextmanager
def audit_database(
    rows: list[dict],
    assignments: list[tuple[int, int]],
) -> Iterator[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    connection = engine.connect()
    connection.exec_driver_sql("ATTACH DATABASE ':memory:' AS identidad")
    connection.exec_driver_sql("""
        CREATE TABLE identidad.roles_aplicacion (
            id_rol INTEGER PRIMARY KEY,
            codigo VARCHAR(32) NOT NULL UNIQUE
        )
    """)
    connection.exec_driver_sql("""
        CREATE TABLE identidad.usuarios_roles (
            id_usuario INTEGER NOT NULL,
            id_rol INTEGER NOT NULL,
            asignado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id_usuario, id_rol)
        )
    """)
    connection.exec_driver_sql("""
        CREATE TABLE identidad.usuarios (
            id_usuario INTEGER PRIMARY KEY,
            id_empleado INTEGER,
            nombre_usuario TEXT
        )
    """)
    connection.exec_driver_sql("""
        CREATE TABLE identidad.empleados (
            id_empleado INTEGER PRIMARY KEY,
            nombre_completo TEXT
        )
    """)
    connection.exec_driver_sql("""
        CREATE TABLE identidad.auditoria_accesos (
            id_auditoria INTEGER PRIMARY KEY,
            id_usuario INTEGER,
            fecha_hora TEXT NOT NULL,
            accion VARCHAR(120) NOT NULL,
            objeto_consultado VARCHAR(255) NOT NULL,
            event_id TEXT,
            microservicio TEXT NOT NULL DEFAULT 'identidad',
            modulo TEXT NOT NULL DEFAULT 'identidad',
            tipo_objeto TEXT,
            id_objeto TEXT,
            resultado TEXT NOT NULL DEFAULT 'SUCCESS',
            metodo_http TEXT,
            ruta TEXT,
            direccion_ip TEXT,
            correlation_id TEXT,
            detalles TEXT NOT NULL DEFAULT '{}'
        )
    """)
    connection.execute(
        text("INSERT INTO identidad.roles_aplicacion (id_rol, codigo) VALUES (:id, :code)"),
        [{"id": 1, "code": "auditor"}, {"id": 2, "code": "administrador"}],
    )
    if assignments:
        connection.execute(
            text("""
                INSERT INTO identidad.usuarios_roles (id_usuario, id_rol)
                VALUES (:id_usuario, :id_rol)
            """),
            [{"id_usuario": user_id, "id_rol": role_id} for user_id, role_id in assignments],
        )
    if rows:
        audit_rows = [
            {
                **row,
                "event_id": row.get("event_id"),
                "microservicio": row.get("microservicio", "identidad"),
                "modulo": row.get("modulo", "identidad"),
                "tipo_objeto": row.get("tipo_objeto"),
                "id_objeto": row.get("id_objeto"),
                "resultado": row.get("resultado", "SUCCESS"),
                "metodo_http": row.get("metodo_http"),
                "ruta": row.get("ruta"),
                "direccion_ip": row.get("direccion_ip"),
                "correlation_id": row.get("correlation_id"),
                "detalles": row.get("detalles", "{}"),
            }
            for row in rows
        ]
        connection.execute(
            text("""
                INSERT INTO identidad.auditoria_accesos
                    (id_auditoria, id_usuario, fecha_hora, accion, objeto_consultado,
                     event_id, microservicio, modulo, tipo_objeto, id_objeto,
                     resultado, metodo_http, ruta, direccion_ip, correlation_id, detalles)
                VALUES
                    (:id_auditoria, :id_usuario, :fecha_hora, :accion, :objeto_consultado,
                     :event_id, :microservicio, :modulo, :tipo_objeto, :id_objeto,
                     :resultado, :metodo_http, :ruta, :direccion_ip, :correlation_id, :detalles)
            """),
            audit_rows,
        )
    connection.commit()
    db = Session(bind=connection)
    try:
        yield db
    finally:
        db.close()
        connection.close()
        engine.dispose()


@pytest.fixture
def auth_token(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setattr(settings, "jwt_secret_key", "identity-management-test-key")
    return create_access_token({"sub": "5"})


def test_employee_create_is_parameterized_and_commits_for_database_audit(
    monkeypatch: pytest.MonkeyPatch,
    auth_token: str,
) -> None:
    monkeypatch.setattr(
        "app.services.identidad.employees.request_service",
        lambda service, method, path, **kwargs: {"id_sede": 1},
    )
    employee = {
        "id_empleado": 22,
        "id_sede": 1,
        "num_documento": "DOC-22",
        "nombre_completo": "Empleado de prueba",
        "cargo": "Operador",
        "correo": None,
        "estado": "activo",
    }
    db = FakeDatabaseSession(FakeResult(employee), FakeResult())
    monkeypatch.setitem(app.dependency_overrides, get_identity_db, lambda: db)

    with TestClient(app) as client:
        response = client.post(
            "/employees",
            json={
                "id_sede": 1,
                "num_documento": "DOC-22",
                "nombre_completo": "Empleado de prueba",
                "cargo": "Operador",
                "correo": None,
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )

    assert response.status_code == 201
    assert response.json() == employee
    assert db.commits == 1
    assert db.statements[0][1]["num_documento"] == "DOC-22"
    assert len(db.statements) == 1
    assert "INSERT INTO identidad.empleados" in db.statements[0][0]


def test_user_creation_hashes_password_and_never_returns_hash(
    monkeypatch: pytest.MonkeyPatch,
    auth_token: str,
) -> None:
    employee = {
        "id_empleado": 9,
        "id_sede": 1,
        "num_documento": "DOC-9",
        "nombre_completo": "Empleado",
        "cargo": "Asesor",
        "correo": None,
        "estado": "activo",
    }
    user = {
        "id_usuario": 11,
        "id_empleado": 9,
        "nombre_usuario": "nuevo",
        "estado": "activo",
        "fecha_creacion": "2026-01-01T10:00:00",
    }
    db = FakeDatabaseSession(FakeResult(employee), FakeResult(user), FakeResult())
    monkeypatch.setitem(app.dependency_overrides, get_identity_db, lambda: db)

    with TestClient(app) as client:
        response = client.post(
            "/users",
            json={
                "id_empleado": 9,
                "nombre_usuario": "nuevo",
                "password": "no-debe-regresarse",
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )

    assert response.status_code == 201
    assert "password_hash" not in response.json()
    assert "password" not in response.json()
    password_hash = db.statements[1][1]["password_hash"]
    assert password_hash.startswith("$argon2")
    assert db.statements[1][1]["password_hash"] != "no-debe-regresarse"
    assert db.commits == 1


def test_generic_user_update_rejects_password_fields(
    auth_token: str,
) -> None:
    with TestClient(app) as client:
        response = client.patch(
            "/users/5",
            json={"password": "not-allowed"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )

    assert response.status_code == 422


def test_password_change_requires_and_replaces_current_hash(
    monkeypatch: pytest.MonkeyPatch,
    auth_token: str,
) -> None:
    db = FakeDatabaseSession(
        FakeResult(
            {
                "id_usuario": 5,
                "id_empleado": 4,
                "nombre_usuario": "usuario",
                "password_hash": hash_password("actual"),
                "estado": "activo",
            }
        ),
        FakeResult(rowcount=1),
        FakeResult(),
    )
    monkeypatch.setitem(app.dependency_overrides, get_identity_db, lambda: db)

    with TestClient(app) as client:
        response = client.post(
            "/auth/password",
            json={"current_password": "actual", "new_password": "nueva"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )

    assert response.status_code == 204
    assert db.statements[1][1]["password_hash"].startswith("$argon2")
    assert db.statements[1][1]["password_hash"] != "nueva"
    assert db.commits == 1


@pytest.mark.parametrize("role_id", [1, 2], ids=["auditor", "administrador"])
def test_audit_roles_read_all_records_in_stable_pages(
    monkeypatch: pytest.MonkeyPatch,
    auth_token: str,
    role_id: int,
) -> None:
    rows = [
        {
            "id_auditoria": 101,
            "id_usuario": 5,
            "fecha_hora": "2026-11-25T10:00:00",
            "accion": "SELECT",
            "objeto_consultado": "identidad.usuarios",
        },
        {
            "id_auditoria": 102,
            "id_usuario": 6,
            "fecha_hora": "2026-11-25T11:00:00",
            "accion": "UPDATE",
            "objeto_consultado": "identidad.usuarios",
        },
        {
            "id_auditoria": 103,
            "id_usuario": 7,
            "fecha_hora": "2026-11-25T11:00:00",
            "accion": "LOGIN",
            "objeto_consultado": "autenticacion",
        },
    ]
    with audit_database(rows, [(5, role_id)]) as db:
        monkeypatch.setitem(app.dependency_overrides, get_identity_db, lambda: db)
        with TestClient(app) as client:
            headers = {"Authorization": f"Bearer {auth_token}"}
            first_page = client.get("/auth/audit?limit=2&offset=0", headers=headers)
            second_page = client.get("/auth/audit?limit=2&offset=2", headers=headers)

    assert first_page.status_code == 200
    assert [row["id_auditoria"] for row in first_page.json()] == [103, 102]
    assert second_page.status_code == 200
    assert [row["id_auditoria"] for row in second_page.json()] == [101]
    assert set(first_page.json()[0]) == {
        "id_auditoria",
        "id_usuario",
        "fecha_hora",
        "accion",
        "objeto_consultado",
        "event_id",
        "microservicio",
        "modulo",
        "tipo_objeto",
        "id_objeto",
        "resultado",
        "metodo_http",
        "ruta",
        "direccion_ip",
        "correlation_id",
        "detalles",
        "nombre_usuario",
        "nombre_completo",
    }


def test_normal_user_cannot_expand_audit_scope_with_claim_or_query_parameters(
    monkeypatch: pytest.MonkeyPatch,
    auth_token: str,
) -> None:
    monkeypatch.setattr(settings, "jwt_secret_key", "identity-management-test-key")
    token_with_untrusted_user_field = create_access_token(
        {"sub": "5", "id_usuario": 6},
    )
    rows = [
        {
            "id_auditoria": 201,
            "id_usuario": 5,
            "fecha_hora": "2026-11-25T10:00:00",
            "accion": "LOGIN",
            "objeto_consultado": "autenticacion",
        },
        {
            "id_auditoria": 202,
            "id_usuario": 6,
            "fecha_hora": "2026-11-25T11:00:00",
            "accion": "SELECT",
            "objeto_consultado": "identidad.usuarios",
        },
    ]
    with audit_database(rows, [(6, 1)]) as db:
        monkeypatch.setitem(app.dependency_overrides, get_identity_db, lambda: db)
        with TestClient(app) as client:
            response = client.get(
                "/auth/audit?limit=100&id_usuario=6&scope=global",
                headers={"Authorization": f"Bearer {token_with_untrusted_user_field}"},
            )

    assert response.status_code == 200
    assert [row["id_auditoria"] for row in response.json()] == [201]


def test_auditor_can_combine_filters_without_changing_stable_pagination(
    monkeypatch: pytest.MonkeyPatch,
    auth_token: str,
) -> None:
    rows = [
        {
            "id_auditoria": 301,
            "id_usuario": 6,
            "fecha_hora": "2026-11-25T10:00:00",
            "accion": "POST /orders",
            "objeto_consultado": "ventas.pedidos",
            "microservicio": "ventas",
            "modulo": "orders",
            "resultado": "SUCCESS",
            "ruta": "/orders",
        },
        {
            "id_auditoria": 302,
            "id_usuario": 7,
            "fecha_hora": "2026-11-25T11:00:00",
            "accion": "POST /products",
            "objeto_consultado": "catalogo.productos",
            "microservicio": "catalogo",
            "modulo": "products",
            "resultado": "DENIED",
            "ruta": "/products",
        },
    ]
    with audit_database(rows, [(5, 1)]) as db:
        monkeypatch.setitem(app.dependency_overrides, get_identity_db, lambda: db)
        with TestClient(app) as client:
            response = client.get(
                "/auth/audit?microservicio=ventas&modulo=orders&accion=post"
                "&resultado=SUCCESS&texto=pedidos",
                headers={"Authorization": f"Bearer {auth_token}"},
            )

    assert response.status_code == 200
    assert [row["id_auditoria"] for row in response.json()] == [301]
    assert response.json()[0]["fecha_hora"].endswith("Z")


def test_audit_endpoint_rejects_an_inverted_date_range(
    monkeypatch: pytest.MonkeyPatch,
    auth_token: str,
) -> None:
    with audit_database([], []) as db:
        monkeypatch.setitem(app.dependency_overrides, get_identity_db, lambda: db)
        with TestClient(app) as client:
            response = client.get(
                "/auth/audit?fecha_desde=2026-11-25T12:00:00Z"
                "&fecha_hasta=2026-11-25T10:00:00Z",
                headers={"Authorization": f"Bearer {auth_token}"},
            )

    assert response.status_code == 422


def test_audit_endpoint_rejects_unauthenticated_requests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "jwt_secret_key", "identity-management-test-key")
    with audit_database([], []) as db:
        monkeypatch.setitem(app.dependency_overrides, get_identity_db, lambda: db)
        with TestClient(app) as client:
            response = client.get("/auth/audit")

    assert response.status_code == 401


@pytest.mark.parametrize("subject", ["0", "-1", "no-numerico", 5])
def test_audit_endpoint_rejects_invalid_jwt_subjects(
    monkeypatch: pytest.MonkeyPatch,
    subject: object,
) -> None:
    monkeypatch.setattr(settings, "jwt_secret_key", "identity-management-test-key")
    token = create_access_token({"sub": subject})
    db = FakeDatabaseSession()
    monkeypatch.setitem(app.dependency_overrides, get_identity_db, lambda: db)

    with TestClient(app) as client:
        response = client.get(
            "/auth/audit",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 401
    assert db.statements == []
