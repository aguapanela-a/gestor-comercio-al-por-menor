
import json
import re
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from jose import JWTError
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.security import bearer_scheme, decode_access_token
from app.services.identidad.dependencies import get_identity_db
from app.shared.audit import AUDIT_SERVICES

router = APIRouter(
    prefix="/internal/audit/events",
    tags=["Auditoría interna"],
)

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


class AuditEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: UUID
    id_usuario: int | None = Field(default=None, gt=0)
    fecha_hora: datetime
    microservicio: str = Field(min_length=1, max_length=40)
    modulo: str = Field(min_length=1, max_length=80)
    accion: str = Field(min_length=1, max_length=120)
    tipo_objeto: str | None = Field(default=None, max_length=160)
    id_objeto: str | None = Field(default=None, max_length=255)
    resultado: Literal["SUCCESS", "FAILURE", "DENIED"]
    metodo_http: str | None = Field(default=None, max_length=12)
    ruta: str | None = Field(default=None, max_length=255)
    direccion_ip: str | None = Field(default=None, max_length=45)
    correlation_id: UUID | None = None
    detalles: dict[str, Any] = Field(default_factory=dict)

    @field_validator("fecha_hora")
    @classmethod
    def normalize_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @field_validator("detalles")
    @classmethod
    def validate_details(cls, value: dict[str, Any]) -> dict[str, Any]:
        def contains_sensitive_key(item: Any) -> bool:
            if isinstance(item, dict):
                return any(
                    _SENSITIVE_KEY.search(str(key))
                    or contains_sensitive_key(child)
                    for key, child in item.items()
                )

            if isinstance(item, list):
                return any(contains_sensitive_key(child) for child in item)

            return False

        if contains_sensitive_key(value):
            raise ValueError(
                "Los detalles no pueden incluir campos sensibles"
            )

        serialized = json.dumps(
            value,
            ensure_ascii=False,
            default=str,
        )

        if len(serialized.encode("utf-8")) > 65_536:
            raise ValueError(
                "Los detalles de auditoría exceden el tamaño permitido"
            )

        return value


def get_audit_service_claims(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any]:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales internas de auditoría no válidas",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise unauthorized

    try:
        claims = decode_access_token(credentials.credentials)
    except JWTError:
        raise unauthorized from None

    if (
        claims.get("token_use") != "audit_ingest"
        or claims.get("service") not in AUDIT_SERVICES
    ):
        raise unauthorized

    return claims


@router.post("", status_code=status.HTTP_202_ACCEPTED)
def receive_audit_event(
    event: AuditEvent,
    claims: dict[str, Any] = Depends(get_audit_service_claims),
    db: Session = Depends(get_identity_db),
) -> dict[str, Any]:
    if (
        claims.get("service") != event.microservicio
        or claims.get("event_id") != str(event.event_id)
        or claims.get("actor_id") != event.id_usuario
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El evento no coincide con la identidad del servicio emisor",
        )

    timestamp = (
        event.fecha_hora
        .astimezone(timezone.utc)
        .replace(tzinfo=None)
    )

    result = db.execute(
        text("""
            INSERT INTO identidad.auditoria_accesos (
                event_id,
                id_usuario,
                fecha_hora,
                accion,
                objeto_consultado,
                microservicio,
                modulo,
                tipo_objeto,
                id_objeto,
                resultado,
                metodo_http,
                ruta,
                direccion_ip,
                correlation_id,
                detalles
            )
            VALUES (
                :event_id,
                :id_usuario,
                :fecha_hora,
                :accion,
                :objeto_consultado,
                :microservicio,
                :modulo,
                :tipo_objeto,
                :id_objeto,
                :resultado,
                :metodo_http,
                :ruta,
                :direccion_ip,
                :correlation_id,
                CAST(:detalles AS JSONB)
            )
            ON CONFLICT (event_id) DO NOTHING
        """),
        {
            "event_id": str(event.event_id),
            "id_usuario": event.id_usuario,
            "fecha_hora": timestamp,
            "accion": event.accion,
            "objeto_consultado": event.tipo_objeto or event.accion,
            "microservicio": event.microservicio,
            "modulo": event.modulo,
            "tipo_objeto": event.tipo_objeto,
            "id_objeto": event.id_objeto,
            "resultado": event.resultado,
            "metodo_http": event.metodo_http,
            "ruta": event.ruta,
            "direccion_ip": event.direccion_ip,
            "correlation_id": (
                str(event.correlation_id)
                if event.correlation_id
                else None
            ),
            "detalles": json.dumps(
                event.detalles,
                ensure_ascii=False,
            ),
        },
    )

    db.commit()

    return {
        "event_id": str(event.event_id),
        "duplicate": result.rowcount == 0,
    }
