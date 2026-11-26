from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.services.catalogo.dependencies import get_catalogo_db
from app.services.catalogo.repositories import (
    create_category,
    get_category,
    list_categories,
    update_category,
)
from app.services.catalogo.schemas import (
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
    CatalogState,
)
from app.shared.audit import set_audit_details

router = APIRouter(prefix="/categories", tags=["Categorías"])


def _commit_or_conflict(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="La operación entra en conflicto con datos existentes",
        ) from None


@router.get("", response_model=list[CategoryResponse])
def read_categories(
    estado: Annotated[CatalogState | None, Query()] = None,
    q: Annotated[str | None, Query(min_length=1, max_length=80)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: Session = Depends(get_catalogo_db),
) -> list[CategoryResponse]:
    rows = list_categories(
        db, estado=estado, search=q, limit=limit, offset=offset
    )
    return [CategoryResponse.model_validate(row) for row in rows]


@router.get("/{id_categoria}", response_model=CategoryResponse)
def read_category(
    id_categoria: Annotated[int, Path(gt=0)],
    db: Session = Depends(get_catalogo_db),
) -> CategoryResponse:
    row = get_category(db, id_categoria)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoría no encontrada",
        )
    return CategoryResponse.model_validate(row)


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def add_category(
    data: CategoryCreate,
    request: Request,
    db: Session = Depends(get_catalogo_db),
) -> CategoryResponse:
    try:
        row = create_category(db, data.model_dump())
        _commit_or_conflict(db)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="El nombre de categoría ya existe") from None
    set_audit_details(
        request,
        object_type="catalogo.categorias",
        object_id=row["id_categoria"],
        after=row,
    )
    return CategoryResponse.model_validate(row)


@router.patch("/{id_categoria}", response_model=CategoryResponse)
def edit_category(
    id_categoria: Annotated[int, Path(gt=0)],
    data: CategoryUpdate,
    request: Request,
    db: Session = Depends(get_catalogo_db),
) -> CategoryResponse:
    before = get_category(db, id_categoria)
    values = data.model_dump(exclude_unset=True)
    if any(value is None and key != "descripcion" for key, value in values.items()):
        raise HTTPException(status_code=422, detail="Los campos requeridos no aceptan null")
    try:
        row = update_category(db, id_categoria, values)
        if row is None:
            db.rollback()
            raise HTTPException(status_code=404, detail="Categoría no encontrada")
        _commit_or_conflict(db)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="El nombre de categoría ya existe") from None
    set_audit_details(
        request,
        object_type="catalogo.categorias",
        object_id=id_categoria,
        before=before,
        after=row,
    )
    return CategoryResponse.model_validate(row)


@router.delete("/{id_categoria}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_category(
    id_categoria: Annotated[int, Path(gt=0)],
    request: Request,
    db: Session = Depends(get_catalogo_db),
) -> None:
    before = get_category(db, id_categoria)
    try:
        row = update_category(db, id_categoria, {"estado": "inactivo"})
        if row is None:
            db.rollback()
            raise HTTPException(status_code=404, detail="Categoría no encontrada")
        _commit_or_conflict(db)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="No fue posible inactivar la categoría") from None
    set_audit_details(
        request,
        object_type="catalogo.categorias",
        object_id=id_categoria,
        before=before,
        after=row,
    )
