from app.services.organizacion.main import app


def test_organizacion_health(assert_health_endpoints) -> None:
    assert_health_endpoints(app, "organizacion")
