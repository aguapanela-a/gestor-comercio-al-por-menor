import asyncio
import json
import logging
import re
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import httpx
from fastapi import Request
from fastapi.responses import JSONResponse, Response
from jose import JWTError
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.config import settings
from app.core.security import create_access_token, decode_access_token

logger = logging.getLogger(__name__)

AUDIT_SERVICES = frozenset({
    "catalogo",
    "organizacion",
    "compras",
    "inventarios",
    "identidad",
    "reportes",
    "ventas",
})

_SENSITIVE_KEY = re.compile(
    r"(password|contras|clave|hash|token|secret|authorization|connection|document|"
    r"identificacion|identification|nit|cedula|correo|email|telefono|phone|direccion|"
    r"address|nombre_completo|nombre_usuario|nombre_cliente|nombre_empleado|"
    r"nombre_persona|nombre_contacto|nombre_destinatario|"
    r"(?:cliente|empleado|usuario|persona|contacto|destinatario)_nombre|"
    r"(?:first|last)[_-]?name|"
    r"(?:customer|client|employee|user|person|contact)[_-]?name|"
    r"apellido|surname|fecha_nacimiento|birth|dob)",
    re.IGNORECASE,
)

current_audit_correlation_id: ContextVar[str | None] = ContextVar(
    "current_audit_correlation_id",
    default=None,
)
current_audit_service: ContextVar[str | None] = ContextVar(
    "current_audit_service",
    default=None,
)


class AuditDeliveryError(RuntimeError):
    pass


@dataclass
class AuditContext:
    service: str
    actor_id: int | None
    correlation_id: str
    method: str
    route: str
    module: str
    action: str
    client_ip: str | None
    object_type: str | None = None
    object_id: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    custom_action: bool = False
    custom_object: bool = False


def _actor_id(request: Request) -> int | None:
    authorization = request.headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None

    try:
        claims = decode_access_token(token)
    except JWTError:
        return None

    subject = claims.get("sub")
    if claims.get("token_use") in {"audit_ingest", "audit_delegation"}:
        return None
    if not isinstance(subject, str) or not subject.isdecimal():
        return None
    actor_id = int(subject)
    return actor_id if actor_id > 0 else None


def _correlation_id(request: Request) -> str:
    supplied = request.headers.get("x-correlation-id")
    if supplied:
        try:
            return str(UUID(supplied))
        except ValueError:
            logger.info("Invalid X-Correlation-ID replaced with a generated value")
    return str(uuid4())


def _route_template(request: Request) -> str:
    route = request.scope.get("route")
    route_path = getattr(route, "path", None)
    return str(route_path or request.url.path)[:255]


def _module_name(service: str, route: str) -> str:
    first_segment = next((part for part in route.split("/") if part), service)
    return first_segment[:80]


def _object_details(route: str) -> tuple[str | None, str | None]:
    parts = [part for part in route.split("/") if part]
    numeric = next((part for part in reversed(parts) if part.isdecimal()), None)
    if numeric is not None:
        index = parts.index(numeric)
        object_name = parts[index - 1] if index > 0 else "recurso"
        return object_name[:160], numeric
    if len(parts) >= 2 and parts[0] == "vistas":
        return "vista", parts[1][:255]
    return (parts[-1][:160] if parts else "api"), None


def build_audit_context(request: Request, service: str) -> AuditContext:
    route = _route_template(request)
    object_type, object_id = _object_details(route)
    return AuditContext(
        service=service,
        actor_id=_actor_id(request),
        correlation_id=_correlation_id(request),
        method=request.method[:12],
        route=route,
        module=_module_name(service, route),
        action=f"{request.method} {route}"[:120],
        client_ip=request.client.host if request.client is not None else None,
        object_type=f"{service}.{object_type}"[:160] if object_type else None,
        object_id=object_id,
    )


def set_audit_details(
    request: Request,
    *,
    action: str | None = None,
    object_type: str | None = None,
    object_id: str | int | None = None,
    before: Any = None,
    after: Any = None,
    details: dict[str, Any] | None = None,
) -> None:
    context: AuditContext | None = getattr(request.state, "audit_context", None)
    if context is None:
        return
    if action:
        context.action = action[:120]
        context.custom_action = True
    if object_type:
        context.object_type = object_type[:160]
    if object_id is not None:
        context.object_id = str(object_id)[:255]
    if object_type or object_id is not None:
        context.custom_object = True
    if details is not None:
        context.details.update(details)
    if before is not None or after is not None:
        context.details["cambios"] = {
            "antes": _json_safe(before),
            "despues": _json_safe(after),
        }


def _json_safe(value: Any, _seen: set[int] | None = None) -> Any:
    seen = _seen if _seen is not None else set()
    if hasattr(value, "model_dump"):
        object_id = id(value)
        if object_id in seen:
            return None
        seen.add(object_id)
        try:
            dumped = value.model_dump(mode="json")
            return None if dumped is value else _json_safe(dumped, seen)
        finally:
            seen.remove(object_id)
    if isinstance(value, dict):
        object_id = id(value)
        if object_id in seen:
            return None
        seen.add(object_id)
        try:
            return {
                str(key): _json_safe(item, seen)
                for key, item in value.items()
                if not _SENSITIVE_KEY.search(str(key))
            }
        finally:
            seen.remove(object_id)
    if isinstance(value, (list, tuple)):
        object_id = id(value)
        if object_id in seen:
            return None
        seen.add(object_id)
        try:
            return [_json_safe(item, seen) for item in value]
        finally:
            seen.remove(object_id)
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat() if value.tzinfo else value.isoformat()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value[:200] if isinstance(value, str) else value
    return str(value)[:200]


def _event_payload(context: AuditContext, status_code: int) -> dict[str, Any]:
    if status_code in (401, 403):
        result = "DENIED"
    elif status_code >= 400:
        result = "FAILURE"
    else:
        result = "SUCCESS"
    details = {"http_status": status_code, **_json_safe(context.details)}
    if len(json.dumps(details, ensure_ascii=False).encode("utf-8")) > 60_000:
        details = {"http_status": status_code, "details_truncated": True}
    return {
        "event_id": str(uuid4()),
        "id_usuario": context.actor_id,
        "fecha_hora": datetime.now(timezone.utc).isoformat(),
        "microservicio": context.service,
        "modulo": context.module,
        "accion": context.action,
        "tipo_objeto": context.object_type,
        "id_objeto": context.object_id,
        "resultado": result,
        "metodo_http": context.method,
        "ruta": context.route,
        "direccion_ip": context.client_ip,
        "correlation_id": context.correlation_id,
        "detalles": details,
    }


def _refresh_route_context(context: AuditContext, request: Request) -> None:
    route = _route_template(request)
    if route == context.route:
        return
    context.route = route
    context.module = _module_name(context.service, route)
    if not context.custom_action:
        context.action = f"{context.method} {route}"[:120]
    if not context.custom_object:
        object_type, object_id = _object_details(route)
        path_values = request.path_params
        if object_id is None:
            object_id = next(
                (str(value) for value in path_values.values() if value is not None),
                None,
            )
        context.object_type = (
            f"{context.service}.{object_type}"[:160] if object_type else None
        )
        context.object_id = object_id[:255] if object_id else None


def registrar_evento(event: dict[str, Any]) -> None:
    service = event["microservicio"]
    event_id = event["event_id"]
    if service not in AUDIT_SERVICES:
        raise AuditDeliveryError("Servicio emisor de auditoría no autorizado")
    if not settings.jwt_secret_key:
        raise AuditDeliveryError("JWT_SECRET_KEY no está configurada para auditar")

    try:
        token = create_access_token(
            {
                "sub": f"service:{service}",
                "token_use": "audit_ingest",
                "service": service,
                "actor_id": event["id_usuario"],
                "event_id": event_id,
            },
            expires_minutes=1,
        )
    except (RuntimeError, ValueError) as error:
        raise AuditDeliveryError(
            f"No se pudo autenticar la entrega del evento {event_id} "
            f"({type(error).__name__})"
        ) from None
    try:
        with httpx.Client(timeout=settings.service_http_timeout_seconds) as client:
            response = client.post(
                f"{settings.identidad_service_url.rstrip('/')}/internal/audit/events",
                json=event,
                headers={"Authorization": f"Bearer {token}"},
            )
    except (httpx.RequestError, httpx.InvalidURL) as error:
        raise AuditDeliveryError(
            f"Identidad no respondió al evento {event_id} ({type(error).__name__})"
        ) from None
    if response.status_code not in (200, 202):
        raise AuditDeliveryError(
            f"Identidad rechazó el evento {event_id} (HTTP {response.status_code})"
        )


def _valid_delegation(
    request: Request,
    correlation_id: str,
    destination_service: str,
) -> bool:
    token = request.headers.get("x-audit-delegation", "")
    if not token:
        return False
    try:
        claims = decode_access_token(token)
    except JWTError:
        return False
    return (
        claims.get("token_use") == "audit_delegation"
        and claims.get("service") in AUDIT_SERVICES
        and claims.get("sub") == f"service:{claims.get('service')}"
        and claims.get("correlation_id") == correlation_id
        and claims.get("destination") == destination_service
    )


def crear_token_delegacion(
    service: str,
    correlation_id: str,
    destination_service: str,
) -> str:
    if service not in AUDIT_SERVICES or destination_service not in AUDIT_SERVICES:
        raise ValueError(f"Servicio de delegación no permitido: {service}")
    return create_access_token(
        {
            "sub": f"service:{service}",
            "token_use": "audit_delegation",
            "service": service,
            "correlation_id": correlation_id,
            "destination": destination_service,
        },
        expires_minutes=1,
    )


class AuditRequestMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, service: str) -> None:
        super().__init__(app)
        if service not in AUDIT_SERVICES:
            raise ValueError(f"Servicio sin auditoría registrada: {service}")
        self.service = service

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        if not settings.audit_capture_enabled or self._should_skip(request.url.path):
            return await call_next(request)

        context = build_audit_context(request, self.service)
        request.state.audit_context = context
        correlation_token: Token[str | None] = current_audit_correlation_id.set(
            context.correlation_id
        )
        service_token: Token[str | None] = current_audit_service.set(self.service)
        delegated = _valid_delegation(request, context.correlation_id, self.service)
        request.state.audit_delegated = delegated
        try:
            response = await call_next(request)
        except Exception:
            if not delegated:
                await self._publish(context, 500)
            raise
        finally:
            current_audit_service.reset(service_token)
            current_audit_correlation_id.reset(correlation_token)

        _refresh_route_context(context, request)
        response.headers["X-Correlation-ID"] = context.correlation_id
        if delegated:
            return response
        if not await self._publish(context, response.status_code):
            response.headers["X-Audit-Status"] = "failed"
            response.headers["X-Audit-Error"] = "identity-unavailable"
            if response.status_code < 400 and request.method.upper() in {
                "POST", "PUT", "PATCH", "DELETE"
            }:
                return JSONResponse(
                    status_code=503,
                    content={
                        "detail": "La operación fue confirmada, pero no se pudo persistir su auditoría.",
                        "business_operation_committed": True,
                        "audit_persisted": False,
                        "retryable": False,
                        "correlation_id": context.correlation_id,
                    },
                    headers={
                        "X-Correlation-ID": context.correlation_id,
                        "X-Audit-Status": "failed",
                        "X-Business-Operation": "committed",
                    },
                )
        else:
            response.headers["X-Audit-Status"] = "persisted"
        return response

    async def _publish(self, context: AuditContext, status_code: int) -> bool:
        try:
            await asyncio.to_thread(registrar_evento, _event_payload(context, status_code))
            return True
        except AuditDeliveryError as error:
            logger.error(
                "Audit event delivery failed for %s %s: %s",
                context.service,
                context.route,
                error,
            )
            return False

    @staticmethod
    def _should_skip(path: str) -> bool:
        return (
            path in {"/health", "/health/database", "/openapi.json"}
            or path.startswith(("/docs", "/redoc", "/internal/audit/events"))
        )
