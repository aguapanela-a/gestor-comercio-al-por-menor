from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.services.organizacion.dependencies import get_organizacion_db
from app.services.organizacion.repositories import (
    create_warehouse,
    get_warehouse,
    list_warehouses,
    site_exists,
    update_warehouse,
)
from app.services.organizacion.schemas import (
    SiteState,
    WarehouseCreate,
    WarehouseResponse,
    WarehouseType,
    WarehouseUpdate,
)

router = APIRouter(prefix="/warehouses", tags=["Almacenes"])


def _commit_or_conflict(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="La operación entra en conflicto con datos existentes",
        ) from None


@router.get("", response_model=list[WarehouseResponse])
def read_warehouses(
    estado: Annotated[SiteState | None, Query()] = None,
    tipo_almacen: Annotated[WarehouseType | None, Query()] = None,
    id_sede: Annotated[int | None, Query(gt=0)] = None,
    q: Annotated[str | None, Query(min_length=1, max_length=80)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=100_000)] = 0,
    db: Session = Depends(get_organizacion_db),
) -> list[WarehouseResponse]:
    rows = list_warehouses(
        db,
        estado=estado,
        tipo_almacen=tipo_almacen,
        id_sede=id_sede,
        search=q,
        limit=limit,
        offset=offset,
    )
    return [WarehouseResponse.model_validate(row) for row in rows]


@router.get("/{id_almacen}", response_model=WarehouseResponse)
def read_warehouse(
    id_almacen: Annotated[int, Path(gt=0)],
    db: Session = Depends(get_organizacion_db),
) -> WarehouseResponse:
    row = get_warehouse(db, id_almacen)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Almacén no encontrado",
        )
    return WarehouseResponse.model_validate(row)


@router.post("", response_model=WarehouseResponse, status_code=status.HTTP_201_CREATED)
def add_warehouse(
    data: WarehouseCreate,
    db: Session = Depends(get_organizacion_db),
) -> WarehouseResponse:
    if not site_exists(db, data.id_sede):
        raise HTTPException(status_code=404, detail="Sede no encontrada")
    try:
        row = create_warehouse(db, data.model_dump())
        _commit_or_conflict(db)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Ya existe un almacén con ese nombre en la sede",
        ) from None
    return WarehouseResponse.model_validate(row)


@router.patch("/{id_almacen}", response_model=WarehouseResponse)
def edit_warehouse(
    id_almacen: Annotated[int, Path(gt=0)],
    data: WarehouseUpdate,
    db: Session = Depends(get_organizacion_db),
) -> WarehouseResponse:
    values = data.model_dump(exclude_unset=True)
    if any(value is None for value in values.values()):
        raise HTTPException(status_code=422, detail="Los campos no aceptan null")
    if "id_sede" in values and not site_exists(db, values["id_sede"]):
        raise HTTPException(status_code=404, detail="Sede no encontrada")
    try:
        row = update_warehouse(db, id_almacen, values)
        if row is None:
            db.rollback()
            raise HTTPException(status_code=404, detail="Almacén no encontrado")
        _commit_or_conflict(db)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="El almacén entra en conflicto con datos existentes",
        ) from None
    return WarehouseResponse.model_validate(row)


@router.delete("/{id_almacen}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_warehouse(
    id_almacen: Annotated[int, Path(gt=0)],
    db: Session = Depends(get_organizacion_db),
) -> None:
    try:
        row = update_warehouse(db, id_almacen, {"estado": "inactivo"})
        if row is None:
            db.rollback()
            raise HTTPException(status_code=404, detail="Almacén no encontrado")
        _commit_or_conflict(db)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="No fue posible inactivar el almacén") from None
