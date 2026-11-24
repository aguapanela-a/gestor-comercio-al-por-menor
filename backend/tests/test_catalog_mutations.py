import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import create_access_token
from app.services.catalogo.dependencies import get_catalogo_db
from app.services.catalogo.main import app


class FakeResult:
    def __init__(self, rows=None) -> None:
        self.rows = rows or []

    def mappings(self):
        return self

    def all(self):
        return self.rows

    def first(self):
        return self.rows[0] if self.rows else None

    def one(self):
        return self.rows[0]


class FakeDatabaseSession:
    def __init__(self, *results) -> None:
        self.results = list(results)
        self.statements = []
        self.commits = 0

    def execute(self, statement, parameters=None):
        self.statements.append((str(statement), parameters))
        return self.results.pop(0) if self.results else FakeResult()

    def commit(self):
        self.commits += 1

    def rollback(self):
        pass


@pytest.fixture
def auth_token(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setattr(settings, "jwt_secret_key", "catalog-mutation-test-key")
    return create_access_token({"sub": "1"})


def test_category_delete_deactivates_instead_of_removing_record(
    monkeypatch: pytest.MonkeyPatch,
    auth_token: str,
) -> None:
    category = {
        "id_categoria": 3,
        "nombre": "Bebidas",
        "descripcion": None,
        "estado": "inactivo",
    }
    db = FakeDatabaseSession(FakeResult([category]))
    monkeypatch.setitem(app.dependency_overrides, get_catalogo_db, lambda: db)

    with TestClient(app) as client:
        response = client.delete(
            "/categories/3",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

    assert response.status_code == 204
    query, parameters = db.statements[0]
    assert "UPDATE catalogo.categorias" in query
    assert parameters["estado"] == "inactivo"
    assert db.commits == 1


def test_product_create_requires_existing_category(
    monkeypatch: pytest.MonkeyPatch,
    auth_token: str,
) -> None:
    product = {
        "id_producto": 4,
        "sku": "P-4",
        "nombre": "Producto",
        "id_categoria": 3,
        "unidad_medida": "unidad",
        "precio_lista": "0.00",
        "estado": "activo",
    }
    db = FakeDatabaseSession(FakeResult([{"1": 1}]), FakeResult([product]))
    monkeypatch.setitem(app.dependency_overrides, get_catalogo_db, lambda: db)

    with TestClient(app) as client:
        response = client.post(
            "/products",
            json={
                "sku": "P-4",
                "nombre": "Producto",
                "id_categoria": 3,
                "unidad_medida": "unidad",
                "precio_lista": "0",
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )

    assert response.status_code == 201
    assert response.json()["id_producto"] == 4
    assert "catalogo.categorias" in db.statements[0][0]
    assert db.commits == 1
