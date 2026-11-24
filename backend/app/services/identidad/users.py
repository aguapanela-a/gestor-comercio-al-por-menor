from typing import Any

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import get_current_user, hash_password, verify_password
from app.services.identidad.dependencies import get_identity_db
from app.services.identidad.repositories import (
    change_user_password,
    create_user,
    get_employee,
    get_user,
    get_user_profile,
    get_user_with_hash,
    list_access_audit,
    list_users,
    record_access,
    update_user,
)
from app.services.identidad.schemas import (
    AccessAuditResponse,
    CurrentUserResponse,
    IdentityState,
    IdentityUserResponse,
    PasswordChangeRequest,
    UserCreate,
    UserUpdate,
)

router = APIRouter(
    prefix="/auth",
    tags=["Autenticación"],
    dependencies=[Depends(get_current_user)],
)

accounts_router = APIRouter(
    prefix="/users",
    tags=["Usuarios"],
    dependencies=[Depends(get_current_user)],
)


def _current_user_id(current_user: dict[str, Any]) -> int:
    subject = current_user.get("sub", "")
    if not isinstance(subject, str) or not subject.isdecimal() or int(subject) < 1:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales de autenticación no válidas",
        )
    return int(subject)


def _commit_or_conflict(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La operación entra en conflicto con datos existentes",
        ) from None


@router.get("/me", response_model=CurrentUserResponse)
def read_current_user(
    current_user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_identity_db),
) -> CurrentUserResponse:
    subject = current_user["sub"]
    if not subject.isdecimal() or int(subject) < 1:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales de autenticación no válidas",
            headers={"WWW-Authenticate": "Bearer"},
        )

    profile = get_user_profile(db, int(subject))
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales de autenticación no válidas",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if profile["estado_usuario"] != "activo" or profile["estado_empleado"] != "activo":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La cuenta se encuentra inactiva",
        )

    return CurrentUserResponse.model_validate(profile)


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    data: PasswordChangeRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_identity_db),
) -> None:
    id_usuario = _current_user_id(current_user)
    user = get_user_with_hash(db, id_usuario)
    if user is None or user["estado"] != "activo":
        raise HTTPException(status_code=401, detail="Credenciales no válidas")
    valid, _ = verify_password(
        data.current_password,
        user["password_hash"],
        user["nombre_usuario"],
    )
    if not valid:
        raise HTTPException(status_code=400, detail="La contraseña actual no es válida")
    if not change_user_password(db, id_usuario, hash_password(data.new_password)):
        db.rollback()
        raise HTTPException(status_code=409, detail="No fue posible cambiar la contraseña")
    record_access(
        db,
        id_usuario=id_usuario,
        accion="contrasena_cambiada",
        objeto_consultado=f"usuarios/{id_usuario}",
    )
    _commit_or_conflict(db)


@router.get("/audit", response_model=list[AccessAuditResponse])
def read_access_audit(
    current_user: dict[str, Any] = Depends(get_current_user),
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=100_000)] = 0,
    db: Session = Depends(get_identity_db),
) -> list[AccessAuditResponse]:
    rows = list_access_audit(
        db,
        id_usuario=_current_user_id(current_user),
        limit=limit,
        offset=offset,
    )
    return [AccessAuditResponse.model_validate(row) for row in rows]


@accounts_router.get("", response_model=list[IdentityUserResponse])
def read_users(
    id_empleado: Annotated[int | None, Query(gt=0)] = None,
    estado: Annotated[IdentityState | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=100_000)] = 0,
    db: Session = Depends(get_identity_db),
) -> list[IdentityUserResponse]:
    rows = list_users(
        db,
        id_empleado=id_empleado,
        estado=estado,
        limit=limit,
        offset=offset,
    )
    return [IdentityUserResponse.model_validate(row) for row in rows]


@accounts_router.get("/{id_usuario}", response_model=IdentityUserResponse)
def read_user(
    id_usuario: Annotated[int, Path(gt=0)],
    db: Session = Depends(get_identity_db),
) -> IdentityUserResponse:
    row = get_user(db, id_usuario)
    if row is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return IdentityUserResponse.model_validate(row)


@accounts_router.post(
    "",
    response_model=IdentityUserResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_user(
    data: UserCreate,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_identity_db),
) -> IdentityUserResponse:
    employee = get_employee(db, data.id_empleado)
    if employee is None:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    if employee["estado"] != "activo":
        raise HTTPException(status_code=409, detail="El empleado está inactivo")
    try:
        row = create_user(
            db,
            id_empleado=data.id_empleado,
            nombre_usuario=data.nombre_usuario,
            password_hash=hash_password(data.password),
        )
        record_access(
            db,
            id_usuario=_current_user_id(current_user),
            accion="usuario_creado",
            objeto_consultado=f"usuarios/{row['id_usuario']}",
        )
        _commit_or_conflict(db)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="El empleado ya tiene un usuario o el nombre de usuario existe",
        ) from None
    return IdentityUserResponse.model_validate(row)


@accounts_router.patch("/{id_usuario}", response_model=IdentityUserResponse)
def edit_user(
    id_usuario: Annotated[int, Path(gt=0)],
    data: UserUpdate,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_identity_db),
) -> IdentityUserResponse:
    values = data.model_dump(exclude_unset=True)
    if any(value is None for value in values.values()):
        raise HTTPException(status_code=422, detail="Los campos no aceptan null")
    try:
        row = update_user(db, id_usuario, values)
        if row is None:
            db.rollback()
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        if values:
            record_access(
                db,
                id_usuario=_current_user_id(current_user),
                accion="usuario_actualizado",
                objeto_consultado=f"usuarios/{id_usuario}",
            )
        _commit_or_conflict(db)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="El nombre de usuario ya existe") from None
    return IdentityUserResponse.model_validate(row)


@accounts_router.delete("/{id_usuario}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_user(
    id_usuario: Annotated[int, Path(gt=0)],
    current_user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_identity_db),
) -> None:
    row = update_user(db, id_usuario, {"estado": "inactivo"})
    if row is None:
        db.rollback()
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    record_access(
        db,
        id_usuario=_current_user_id(current_user),
        accion="usuario_inactivado",
        objeto_consultado=f"usuarios/{id_usuario}",
    )
    _commit_or_conflict(db)


__all__ = ["accounts_router", "router"]
