from typing import Any

import httpx

from app.core.config import settings
from app.shared.exceptions import RemoteServiceError

SERVICE_URL_SETTINGS = {
    "identidad": "identidad_service_url",
    "catalogo": "catalogo_service_url",
    "organizacion": "organizacion_service_url",
    "compras": "compras_service_url",
    "inventarios": "inventarios_service_url",
    "ventas": "ventas_service_url",
}


def request_service(
    service: str,
    method: str,
    path: str,
    *,
    bearer_token: str,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | list[Any] | None = None,
) -> Any:
    setting_name = SERVICE_URL_SETTINGS.get(service)
    if setting_name is None:
        raise ValueError(f"Unknown service: {service}")
    base_url = getattr(settings, setting_name).rstrip("/")
    headers = {"Authorization": f"Bearer {bearer_token}"}

    try:
        with httpx.Client(timeout=settings.service_http_timeout_seconds) as client:
            response = client.request(
                method,
                f"{base_url}/{path.lstrip('/')}",
                headers=headers,
                params=params,
                json=json_body,
            )
    except httpx.RequestError as error:
        raise RemoteServiceError(
            service,
            503,
            f"El servicio {service} no está disponible",
        ) from error

    if response.status_code < 200 or response.status_code >= 300:
        raise RemoteServiceError(
            service,
            response.status_code,
            f"El servicio {service} rechazó la operación",
        )
    try:
        return response.json()
    except ValueError as error:
        raise RemoteServiceError(
            service,
            502,
            f"El servicio {service} devolvió una respuesta inválida",
        ) from error


__all__ = ["request_service"]
