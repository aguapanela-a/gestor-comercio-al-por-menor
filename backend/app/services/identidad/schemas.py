from uuid import UUID
import json
from datetime import datetime, timezone
from typing import Literal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator


IdentityState = Literal["activo", "inactivo"]


class IdentityInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LoginRequest(IdentityInput):
    nombre_usuario: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    id_usuario: int
    id_empleado: int
    nombre_usuario: str
    nombre_completo: str
    cargo: str
    id_sede: int


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class CurrentUserResponse(BaseModel):
    id_usuario: int
    id_empleado: int
    nombre_usuario: str
    nombre_completo: str
    cargo: str
    id_sede: int
    correo: str | None


class EmployeeCreate(IdentityInput):
    id_sede: int = Field(gt=0)
    num_documento: str = Field(min_length=1, max_length=20)
    nombre_completo: str = Field(min_length=1, max_length=120)
    cargo: str = Field(min_length=1, max_length=60)
    correo: str | None = Field(default=None, max_length=100)
    estado: IdentityState = "activo"


class EmployeeUpdate(IdentityInput):
    id_sede: int | None = Field(default=None, gt=0)
    num_documento: str | None = Field(default=None, min_length=1, max_length=20)
    nombre_completo: str | None = Field(default=None, min_length=1, max_length=120)
    cargo: str | None = Field(default=None, min_length=1, max_length=60)
    correo: str | None = Field(default=None, max_length=100)
    estado: IdentityState | None = None


class EmployeeResponse(BaseModel):
    id_empleado: int
    id_sede: int
    num_documento: str
    nombre_completo: str
    cargo: str
    correo: str | None
    estado: IdentityState


class UserCreate(IdentityInput):
    id_empleado: int = Field(gt=0)
    nombre_usuario: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)


class UserUpdate(IdentityInput):
    nombre_usuario: str | None = Field(default=None, min_length=1, max_length=50)
    estado: IdentityState | None = None


class IdentityUserResponse(BaseModel):
    id_usuario: int
    id_empleado: int
    nombre_usuario: str
    estado: IdentityState
    fecha_creacion: datetime


class PasswordChangeRequest(IdentityInput):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=1, max_length=128)


class AccessAuditResponse(BaseModel):
    id_auditoria: int
    id_usuario: int | None
    fecha_hora: datetime
    accion: str | None
    objeto_consultado: str | None
    event_id: UUID | str | None = None
    microservicio: str
    modulo: str
    tipo_objeto: str | None
    id_objeto: str | None
    resultado: Literal["SUCCESS", "FAILURE", "DENIED"]
    metodo_http: str | None
    ruta: str | None
    direccion_ip: str | None
    correlation_id: UUID | str | None
    detalles: dict[str, Any]
    nombre_usuario: str | None = None
    nombre_completo: str | None = None

    @field_validator("detalles", mode="before")
    @classmethod
    def decode_details(cls, value: Any) -> dict[str, Any]:
        if isinstance(value, str):
            value = json.loads(value)
        if not isinstance(value, dict):
            raise ValueError("Los detalles de auditorÃ­a deben ser un objeto JSON")
        return value

    @field_serializer("fecha_hora")
    def serialize_timestamp(self, value: datetime) -> datetime:
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


__all__ = [
    "AccessAuditResponse",
    "CurrentUserResponse",
    "EmployeeCreate",
    "EmployeeResponse",
    "EmployeeUpdate",
    "IdentityState",
    "IdentityUserResponse",
    "LoginRequest",
    "LoginResponse",
    "PasswordChangeRequest",
    "UserCreate",
    "UserResponse",
    "UserUpdate",
]
