from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import create_access_token
from app.services.catalogo.dependencies import get_catalogo_db
from app.services.catalogo.main import app


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
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows
        self.statements: list[tuple[str, dict]] = []

    def execute(self, statement, parameters: dict) -> FakeResult:
        self.statements.append((str(statement), parameters))
        return FakeResult(self.rows)


def test_catalogo_health(assert_health_endpoints) -> None:
    assert_health_endpoints(app, "catalogo")


def test_catalog_endpoints_require_a_token(monkeypatch: pytest.MonkeyPatch) -> None:
    db = FakeDatabaseSession([])
    monkeypatch.setitem(app.dependency_overrides, get_catalogo_db, lambda: db)

    with TestClient(app) as client:
        response = client.get("/products")

    assert response.status_code == 401
    assert db.statements == []


def test_product_list_filters_and_returns_catalog_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "jwt_secret_key", "catalog-test-signing-key")
    db = FakeDatabaseSession(
        [
            {
                "id_producto": 12,
                "sku": "CAT-12",
                "nombre": "Producto de prueba",
                "id_categoria": 3,
                "unidad_medida": "unidad",
                "precio_lista": Decimal("12.50"),
                "estado": "inactivo",
            }
        ]
    )
    monkeypatch.setitem(app.dependency_overrides, get_catalogo_db, lambda: db)
    token = create_access_token({"sub": "1"})

    with TestClient(app) as client:
        response = client.get(
            "/products",
            params={
                "estado": "inactivo",
                "id_categoria": 3,
                "q": "CAT",
                "limit": 10,
                "offset": 5,
            },
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    assert response.json()[0]["id_producto"] == 12
    assert response.json()[0]["precio_lista"] == "12.50"
    query, parameters = db.statements[0]
    assert "catalogo.productos" in query
    assert parameters == {
        "estado": "inactivo",
        "limit": 10,
        "offset": 5,
        "id_categoria": 3,
        "search": "%CAT%",
    }


def test_missing_category_returns_404(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "jwt_secret_key", "catalog-test-signing-key")
    db = FakeDatabaseSession([])
    monkeypatch.setitem(app.dependency_overrides, get_catalogo_db, lambda: db)
    token = create_access_token({"sub": "1"})

    with TestClient(app) as client:
        response = client.get(
            "/categories/999",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 404
