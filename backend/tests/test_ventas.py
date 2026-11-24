from app.services.ventas.main import app


def test_ventas_health(assert_health_endpoints) -> None:
    assert_health_endpoints(app, "ventas")
