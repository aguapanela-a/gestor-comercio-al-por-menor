import pytest

from app.core.config import settings
from app.shared.clients import request_service
from app.shared.exceptions import RemoteServiceError


class FakeResponse:
    def __init__(self, status_code=200, payload=None) -> None:
        self.status_code = status_code
        self.payload = payload

    def json(self):
        return self.payload


class FakeClient:
    def __init__(self, response) -> None:
        self.response = response
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def request(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self.response


def test_internal_http_client_uses_configured_url_and_forwards_jwt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = FakeClient(FakeResponse(payload={"id_producto": 4}))
    monkeypatch.setattr("app.shared.clients.httpx.Client", lambda **kwargs: client)
    monkeypatch.setattr(settings, "catalogo_service_url", "http://catalogo.test/")
    monkeypatch.setattr(settings, "service_http_timeout_seconds", 2.5)

    result = request_service(
        "catalogo",
        "GET",
        "/products/4",
        bearer_token="opaque-token",
    )

    assert result == {"id_producto": 4}
    args, kwargs = client.calls[0]
    assert args == ("GET", "http://catalogo.test/products/4")
    assert kwargs["headers"]["Authorization"] == "Bearer opaque-token"


def test_internal_http_client_surfaces_downstream_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = FakeClient(FakeResponse(status_code=404, payload={"detail": "hidden"}))
    monkeypatch.setattr("app.shared.clients.httpx.Client", lambda **kwargs: client)

    with pytest.raises(RemoteServiceError) as error:
        request_service(
            "organizacion",
            "GET",
            "/warehouses/8",
            bearer_token="opaque-token",
        )

    assert error.value.service == "organizacion"
    assert error.value.status_code == 404
    assert "hidden" not in str(error.value)
