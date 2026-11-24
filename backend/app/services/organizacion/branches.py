from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.services.organizacion.dependencies import get_organizacion_db
from app.services.organizacion.repositories import (
    create_site,
    get_site,
    list_sites,
    update_site,
)
from app.services.organizacion.schemas import (
    SiteCreate,
    SiteResponse,
    SiteState,
    SiteType,
    SiteUpdate,
)

router = APIRouter(prefix="/sedes", tags=["Sedes"])


def _commit_or_conflict(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="La operación entra en conflicto con datos existentes",
        ) from None


@router.get("", response_model=list[SiteResponse])
def read_sites(
    estado: Annotated[SiteState | None, Query()] = None,
    tipo_sede: Annotated[SiteType | None, Query()] = None,
    q: Annotated[str | None, Query(min_length=1, max_length=80)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=100_000)] = 0,
    db: Session = Depends(get_organizacion_db),
) -> list[SiteResponse]:
    rows = list_sites(
        db,
        estado=estado,
        tipo_sede=tipo_sede,
        search=q,
        limit=limit,
        offset=offset,
    )
    return [SiteResponse.model_validate(row) for row in rows]


@router.get("/{id_sede}", response_model=SiteResponse)
def read_site(
    id_sede: Annotated[int, Path(gt=0)],
    db: Session = Depends(get_organizacion_db),
) -> SiteResponse:
    row = get_site(db, id_sede)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sede no encontrada",
        )
    return SiteResponse.model_validate(row)


@router.post("", response_model=SiteResponse, status_code=status.HTTP_201_CREATED)
def add_site(
    data: SiteCreate,
    db: Session = Depends(get_organizacion_db),
) -> SiteResponse:
    try:
        row = create_site(db, data.model_dump())
        _commit_or_conflict(db)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="El nombre de sede ya existe") from None
    return SiteResponse.model_validate(row)


@router.patch("/{id_sede}", response_model=SiteResponse)
def edit_site(
    id_sede: Annotated[int, Path(gt=0)],
    data: SiteUpdate,
    db: Session = Depends(get_organizacion_db),
) -> SiteResponse:
    values = data.model_dump(exclude_unset=True)
    if any(value is None for value in values.values()):
        raise HTTPException(status_code=422, detail="Los campos no aceptan null")
    try:
        row = update_site(db, id_sede, values)
        if row is None:
            db.rollback()
            raise HTTPException(status_code=404, detail="Sede no encontrada")
        _commit_or_conflict(db)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="El nombre de sede ya existe") from None
    return SiteResponse.model_validate(row)


@router.delete("/{id_sede}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_site(
    id_sede: Annotated[int, Path(gt=0)],
    db: Session = Depends(get_organizacion_db),
) -> None:
    try:
        row = update_site(db, id_sede, {"estado": "inactivo"})
        if row is None:
            db.rollback()
            raise HTTPException(status_code=404, detail="Sede no encontrada")
        _commit_or_conflict(db)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="No fue posible inactivar la sede") from None
