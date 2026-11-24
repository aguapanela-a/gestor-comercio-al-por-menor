from app.services.inventarios.main import app


def test_inventarios_health(assert_health_endpoints) -> None:
    assert_health_endpoints(app, "inventarios")
