from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.shared.clients import request_service
from app.shared.exceptions import RemoteServiceError
from app.services.identidad.dependencies import get_identity_db
from app.services.identidad.repositories import (
    create_employee,
    get_employee,
    list_employees,
    record_access,
    update_employee,
)
from app.services.identidad.schemas import (
    EmployeeCreate,
    EmployeeResponse,
    EmployeeUpdate,
    IdentityState,
)

router = APIRouter(
    prefix="/employees",
    tags=["Empleados"],
    dependencies=[Depends(get_current_user)],
)


def _actor_id(current_user: dict[str, Any]) -> int:
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


def _validate_site_reference(request: Request, id_sede: int) -> None:
    authorization = request.headers.get("authorization", "")
    scheme, _, bearer_token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not bearer_token:
        raise HTTPException(status_code=401, detail="Credenciales de autenticación no válidas")
    try:
        site = request_service(
            "organizacion",
            "GET",
            f"/sedes/{id_sede}",
            bearer_token=bearer_token,
        )
    except RemoteServiceError as error:
        if error.status_code == 404:
            raise HTTPException(status_code=422, detail="La sede indicada no existe") from None
        raise HTTPException(
            status_code=503 if error.status_code == 503 else 502,
            detail="No fue posible validar la sede en Organización",
        ) from None
    if not isinstance(site, dict) or site.get("id_sede") != id_sede:
        raise HTTPException(
            status_code=502,
            detail="Organización devolvió una respuesta inválida",
        )


@router.get("", response_model=list[EmployeeResponse])
def read_employees(
    id_sede: Annotated[int | None, Query(gt=0)] = None,
    num_documento: Annotated[str | None, Query(min_length=1, max_length=20)] = None,
    estado: Annotated[IdentityState | None, Query()] = None,
    q: Annotated[str | None, Query(min_length=1, max_length=120)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=100_000)] = 0,
    db: Session = Depends(get_identity_db),
) -> list[EmployeeResponse]:
    rows = list_employees(
        db,
        id_sede=id_sede,
        num_documento=num_documento,
        estado=estado,
        search=q,
        limit=limit,
        offset=offset,
    )
    return [EmployeeResponse.model_validate(row) for row in rows]


@router.get("/{id_empleado}", response_model=EmployeeResponse)
def read_employee(
    id_empleado: Annotated[int, Path(gt=0)],
    db: Session = Depends(get_identity_db),
) -> EmployeeResponse:
    row = get_employee(db, id_empleado)
    if row is None:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    return EmployeeResponse.model_validate(row)


@router.post("", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
def add_employee(
    data: EmployeeCreate,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_identity_db),
) -> EmployeeResponse:
    _validate_site_reference(request, data.id_sede)
    try:
        row = create_employee(db, data.model_dump())
        record_access(
            db,
            id_usuario=_actor_id(current_user),
            accion="empleado_creado",
            objeto_consultado=f"empleados/{row['id_empleado']}",
        )
        _commit_or_conflict(db)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El documento del empleado ya existe o hay una referencia inválida",
        ) from None
    return EmployeeResponse.model_validate(row)


@router.patch("/{id_empleado}", response_model=EmployeeResponse)
def edit_employee(
    id_empleado: Annotated[int, Path(gt=0)],
    data: EmployeeUpdate,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_identity_db),
) -> EmployeeResponse:
    values = data.model_dump(exclude_unset=True)
    if any(value is None and key != "correo" for key, value in values.items()):
        raise HTTPException(status_code=422, detail="Los campos requeridos no aceptan null")
    if "id_sede" in values:
        _validate_site_reference(request, values["id_sede"])
    try:
        row = update_employee(db, id_empleado, values)
        if row is None:
            db.rollback()
            raise HTTPException(status_code=404, detail="Empleado no encontrado")
        if values:
            record_access(
                db,
                id_usuario=_actor_id(current_user),
                accion="empleado_actualizado",
                objeto_consultado=f"empleados/{id_empleado}",
            )
        _commit_or_conflict(db)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La actualización entra en conflicto con datos existentes",
        ) from None
    return EmployeeResponse.model_validate(row)


@router.delete("/{id_empleado}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_employee(
    id_empleado: Annotated[int, Path(gt=0)],
    current_user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_identity_db),
) -> None:
    try:
        row = update_employee(db, id_empleado, {"estado": "inactivo"})
        if row is None:
            db.rollback()
            raise HTTPException(status_code=404, detail="Empleado no encontrado")
        record_access(
            db,
            id_usuario=_actor_id(current_user),
            accion="empleado_inactivado",
            objeto_consultado=f"empleados/{id_empleado}",
        )
        _commit_or_conflict(db)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="No fue posible inactivar el empleado",
        ) from None


__all__ = ["router"]
