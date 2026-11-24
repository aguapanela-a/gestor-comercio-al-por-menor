from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.services.identidad.dependencies import get_identity_db
from app.services.identidad.schemas import LoginRequest, LoginResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest, db: Session = Depends(get_identity_db)) -> LoginResponse:
    query = text("""
        SELECT u.id_usuario, u.id_empleado, u.nombre_usuario, u.password_hash,
               u.estado AS estado_usuario, e.estado AS estado_empleado,
               e.nombre_completo, e.cargo, e.id_sede
        FROM identidad.usuarios u
        INNER JOIN identidad.empleados e ON e.id_empleado = u.id_empleado
        WHERE u.nombre_usuario = :nombre_usuario
    """)
    user = db.execute(
        query,
        {"nombre_usuario": data.nombre_usuario},
    ).mappings().first()

    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Usuario o contraseña incorrectos",
    )
    if not user:
        raise credentials_error

    if user["estado_usuario"] != "activo" or user["estado_empleado"] != "activo":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La cuenta se encuentra inactiva",
        )

    valid, needs_upgrade = verify_password(
        data.password,
        user["password_hash"],
        user["nombre_usuario"],
    )
    if not valid:
        raise credentials_error

    if needs_upgrade:
        db.execute(
            text("""
                UPDATE identidad.usuarios
                SET password_hash = :password_hash
                WHERE id_usuario = :id_usuario
            """),
            {
                "password_hash": hash_password(data.password),
                "id_usuario": user["id_usuario"],
            },
        )

    db.execute(
        text("""
            INSERT INTO identidad.auditoria_accesos (id_usuario, accion, objeto_consultado)
            VALUES (:id_usuario, :accion, :objeto)
        """),
        {
            "id_usuario": user["id_usuario"],
            "accion": "inicio_sesion",
            "objeto": "autenticacion",
        },
    )

    token = create_access_token(
        {
            "sub": str(user["id_usuario"]),
            "id_usuario": user["id_usuario"],
            "id_empleado": user["id_empleado"],
            "cargo": user["cargo"],
            "id_sede": user["id_sede"],
        }
    )
    db.commit()

    return LoginResponse(
        access_token=token,
        user=UserResponse(
            id_usuario=user["id_usuario"],
            id_empleado=user["id_empleado"],
            nombre_usuario=user["nombre_usuario"],
            nombre_completo=user["nombre_completo"],
            cargo=user["cargo"],
            id_sede=user["id_sede"],
        ),
    )

__all__ = ["router"]
