from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.services.catalogo.dependencies import get_catalogo_db
from app.services.catalogo.repositories import (
    category_exists,
    create_product,
    get_product,
    list_products,
    update_product,
)
from app.services.catalogo.schemas import (
    CatalogState,
    ProductCreate,
    ProductResponse,
    ProductUpdate,
)
from app.shared.audit import set_audit_details

router = APIRouter(prefix="/products", tags=["Productos"])


def _commit_or_conflict(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="La operación entra en conflicto con datos existentes",
        ) from None


@router.get("", response_model=list[ProductResponse])
def read_products(
    estado: Annotated[CatalogState, Query()] = "activo",
    id_categoria: Annotated[int | None, Query(gt=0)] = None,
    q: Annotated[str | None, Query(min_length=1, max_length=120)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: Session = Depends(get_catalogo_db),
) -> list[ProductResponse]:
    rows = list_products(
        db,
        estado=estado,
        id_categoria=id_categoria,
        search=q,
        limit=limit,
        offset=offset,
    )
    return [ProductResponse.model_validate(row) for row in rows]


@router.get("/{id_producto}", response_model=ProductResponse)
def read_product(
    id_producto: Annotated[int, Path(gt=0)],
    db: Session = Depends(get_catalogo_db),
) -> ProductResponse:
    row = get_product(db, id_producto)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado",
        )
    return ProductResponse.model_validate(row)


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def add_product(
    data: ProductCreate,
    request: Request,
    db: Session = Depends(get_catalogo_db),
) -> ProductResponse:
    if not category_exists(db, data.id_categoria):
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    try:
        row = create_product(db, data.model_dump())
        _commit_or_conflict(db)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="El SKU ya existe o el producto entra en conflicto con datos existentes",
        ) from None
    set_audit_details(
        request,
        object_type="catalogo.productos",
        object_id=row["id_producto"],
        after=row,
    )
    return ProductResponse.model_validate(row)


@router.patch("/{id_producto}", response_model=ProductResponse)
def edit_product(
    id_producto: Annotated[int, Path(gt=0)],
    data: ProductUpdate,
    request: Request,
    db: Session = Depends(get_catalogo_db),
) -> ProductResponse:
    before = get_product(db, id_producto)
    values = data.model_dump(exclude_unset=True)
    if any(value is None for value in values.values()):
        raise HTTPException(status_code=422, detail="Los campos no aceptan null")
    if "id_categoria" in values and not category_exists(db, values["id_categoria"]):
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    try:
        row = update_product(db, id_producto, values)
        if row is None:
            db.rollback()
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        _commit_or_conflict(db)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="El SKU ya existe o el producto entra en conflicto con datos existentes",
        ) from None
    set_audit_details(
        request,
        object_type="catalogo.productos",
        object_id=id_producto,
        before=before,
        after=row,
    )
    return ProductResponse.model_validate(row)


@router.delete("/{id_producto}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_product(
    id_producto: Annotated[int, Path(gt=0)],
    request: Request,
    db: Session = Depends(get_catalogo_db),
) -> None:
    before = get_product(db, id_producto)
    try:
        row = update_product(db, id_producto, {"estado": "inactivo"})
        if row is None:
            db.rollback()
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        _commit_or_conflict(db)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="No fue posible inactivar el producto") from None
    set_audit_details(
        request,
        object_type="catalogo.productos",
        object_id=id_producto,
        before=before,
        after=row,
    )
