from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


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
