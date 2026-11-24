import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.core import database
from app.core.config import settings
from app.core.security import create_access_token
from app.services.organizacion.dependencies import get_organizacion_db
from app.services.organizacion.main import app


class FakeResult:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows

    def mappings(self) -> "FakeResult":
        return self

    def all(self) -> list[dict]:
        return self.rows

    def first(self) -> dict | None:
        return self.rows[0] if self.rows else None


class FakeDatabaseSession:
    def __init__(self, rows: list[dict] | None = None) -> None:
        self.rows = rows or []
        self.statements: list[tuple[str, dict]] = []
        self.closed = False

    def execute(self, statement, parameters: dict) -> FakeResult:
        self.statements.append((str(statement), parameters))
        return FakeResult(self.rows)

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def auth_token(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setattr(settings, "jwt_secret_key", "organization-test-signing-key")
    return create_access_token({"sub": "1"})


@pytest.fixture
def organization_db(monkeypatch: pytest.MonkeyPatch):
    db = FakeDatabaseSession()
    monkeypatch.setitem(
        app.dependency_overrides,
        get_organizacion_db,
        lambda: db,
    )
    return db


def test_organizacion_health(assert_health_endpoints) -> None:
    assert_health_endpoints(app, "organizacion")


@pytest.mark.parametrize(
    "path",
    ["/sedes", "/sedes/1", "/warehouses", "/warehouses/1"],
)
def test_all_organization_endpoints_require_valid_jwt(
    path: str,
    monkeypatch: pytest.MonkeyPatch,
    organization_db: FakeDatabaseSession,
) -> None:
    monkeypatch.setattr(settings, "jwt_secret_key", "organization-test-signing-key")
    expired = jwt.encode(
        {"sub": "1", "exp": 0},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    invalid_signature = jwt.encode(
        {"sub": "1", "exp": 4_102_444_800},
        "different-test-signing-key",
        algorithm=settings.jwt_algorithm,
    )
    malformed_tokens = ["not-a-jwt", invalid_signature, expired]

    with TestClient(app) as client:
        responses = [client.get(path)]
        responses.extend(
            client.get(path, headers={"Authorization": f"Bearer {token}"})
            for token in malformed_tokens
        )

    assert [response.status_code for response in responses] == [401, 401, 401, 401]
    assert organization_db.statements == []


def test_site_list_filters_and_pagination(
    monkeypatch: pytest.MonkeyPatch,
    auth_token: str,
) -> None:
    db = FakeDatabaseSession(
        [
            {
                "id_sede": 4,
                "nombre": "Centro de Distribución",
                "ciudad": "Barranquilla",
                "direccion": "Zona Industrial",
                "tipo_sede": "distribucion",
                "estado": "activo",
            }
        ]
    )
    monkeypatch.setitem(app.dependency_overrides, get_organizacion_db, lambda: db)

    with TestClient(app) as client:
        response = client.get(
            "/sedes",
            params={
                "estado": "activo",
                "tipo_sede": "distribucion",
                "limit": 20,
                "offset": 40,
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )

    assert response.status_code == 200
    assert response.json()[0]["id_sede"] == 4
    query, parameters = db.statements[0]
    assert "FROM organizacion.sedes" in query
    assert "estado = :estado" in query
    assert "tipo_sede = :tipo_sede" in query
    assert "ORDER BY id_sede" in query
    assert parameters == {
        "limit": 20,
        "offset": 40,
        "estado": "activo",
        "tipo_sede": "distribucion",
    }


def test_warehouse_list_filters_and_pagination(
    monkeypatch: pytest.MonkeyPatch,
    auth_token: str,
) -> None:
    db = FakeDatabaseSession(
        [
            {
                "id_almacen": 7,
                "id_sede": 4,
                "nombre": "Almacén Principal",
                "tipo_almacen": "principal",
                "estado": "activo",
            }
        ]
    )
    monkeypatch.setitem(app.dependency_overrides, get_organizacion_db, lambda: db)

    with TestClient(app) as client:
        response = client.get(
            "/warehouses",
            params={
                "estado": "activo",
                "tipo_almacen": "principal",
                "id_sede": 4,
                "limit": 25,
                "offset": 10,
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )

    assert response.status_code == 200
    assert response.json()[0]["id_almacen"] == 7
    query, parameters = db.statements[0]
    assert "FROM organizacion.almacenes" in query
    assert "estado = :estado" in query
    assert "tipo_almacen = :tipo_almacen" in query
    assert "id_sede = :id_sede" in query
    assert "ORDER BY id_almacen" in query
    assert parameters == {
        "limit": 25,
        "offset": 10,
        "estado": "activo",
        "tipo_almacen": "principal",
        "id_sede": 4,
    }


@pytest.mark.parametrize(
    ("path", "expected_id"),
    [("/sedes/2", "id_sede"), ("/warehouses/7", "id_almacen")],
)
def test_individual_resources_return_data(
    path: str,
    expected_id: str,
    monkeypatch: pytest.MonkeyPatch,
    auth_token: str,
) -> None:
    if expected_id == "id_sede":
        rows = {
            "id_sede": 2,
            "nombre": "Sede Cali",
            "ciudad": "Cali",
            "direccion": "Avenida 6",
            "tipo_sede": "comercial",
            "estado": "activo",
        }
    else:
        rows = {
            "id_almacen": 7,
            "id_sede": 2,
            "nombre": "Almacén de Venta",
            "tipo_almacen": "venta",
            "estado": "activo",
        }
    db = FakeDatabaseSession([rows])
    monkeypatch.setitem(app.dependency_overrides, get_organizacion_db, lambda: db)

    with TestClient(app) as client:
        response = client.get(
            path,
            headers={"Authorization": f"Bearer {auth_token}"},
        )

    assert response.status_code == 200
    assert expected_id in response.json()


@pytest.mark.parametrize("path", ["/sedes/999", "/warehouses/999"])
def test_missing_individual_resources_return_404(
    path: str,
    monkeypatch: pytest.MonkeyPatch,
    auth_token: str,
) -> None:
    db = FakeDatabaseSession()
    monkeypatch.setitem(app.dependency_overrides, get_organizacion_db, lambda: db)

    with TestClient(app) as client:
        response = client.get(
            path,
            headers={"Authorization": f"Bearer {auth_token}"},
        )

    assert response.status_code == 404


@pytest.mark.parametrize(
    ("path", "params"),
    [
        ("/sedes", {"estado": "deshabilitado"}),
        ("/sedes", {"tipo_sede": "mixta"}),
        ("/warehouses", {"estado": "deshabilitado"}),
        ("/warehouses", {"tipo_almacen": "temporal"}),
        ("/warehouses", {"id_sede": 0}),
        ("/sedes", {"limit": 0}),
        ("/warehouses", {"limit": 101}),
        ("/sedes", {"offset": -1}),
        ("/warehouses", {"offset": 100001}),
    ],
)
def test_invalid_filter_and_pagination_values_return_422(
    path: str,
    params: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
    auth_token: str,
    organization_db: FakeDatabaseSession,
) -> None:
    with TestClient(app) as client:
        response = client.get(
            path,
            params=params,
            headers={"Authorization": f"Bearer {auth_token}"},
        )

    assert response.status_code == 422
    assert organization_db.statements == []


@pytest.mark.parametrize("path", ["/sedes", "/warehouses"])
def test_list_endpoints_use_safe_pagination_defaults(
    path: str,
    monkeypatch: pytest.MonkeyPatch,
    auth_token: str,
) -> None:
    db = FakeDatabaseSession()
    monkeypatch.setitem(app.dependency_overrides, get_organizacion_db, lambda: db)

    with TestClient(app) as client:
        response = client.get(
            path,
            headers={"Authorization": f"Bearer {auth_token}"},
        )

    assert response.status_code == 200
    assert db.statements[0][1] == {"limit": 50, "offset": 0}
    assert "ORDER BY" in db.statements[0][0]


def test_database_dependency_closes_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = FakeDatabaseSession()
    monkeypatch.setattr(database, "get_engine", lambda _service: object())
    monkeypatch.setitem(
        database.SESSION_FACTORIES,
        "organizacion",
        lambda: session,
    )

    dependency = get_organizacion_db()
    assert next(dependency) is session
    dependency.close()

    assert session.closed
