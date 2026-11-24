from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
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

__all__ = ["LoginRequest", "LoginResponse", "UserResponse"]
