from app.services.compras.main import app


def test_compras_health(assert_health_endpoints) -> None:
    assert_health_endpoints(app, "compras")
