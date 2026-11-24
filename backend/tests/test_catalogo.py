from app.services.catalogo.main import app


def test_catalogo_health(assert_health_endpoints) -> None:
    assert_health_endpoints(app, "catalogo")
