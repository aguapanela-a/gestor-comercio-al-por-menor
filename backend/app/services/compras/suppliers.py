from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.services.compras.dependencies import get_compras_db
from app.services.compras.repositories import (
    create_supplier,
    deactivate_product_supplier,
    get_product_supplier,
    get_supplier,
    list_product_suppliers,
    list_suppliers,
    update_supplier,
    upsert_product_supplier,
)
from app.services.compras.schemas import (
    ProductSupplierInput,
    ProductSupplierResponse,
    ResourceState,
    SupplierCreate,
    SupplierResponse,
    SupplierUpdate,
)
from app.shared.clients import request_service
from app.shared.exceptions import RemoteServiceError
from app.shared.audit import set_audit_details

router = APIRouter(tags=["Proveedores"])


def _commit_or_conflict(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="La operación entra en conflicto con datos existentes",
        ) from None


def _bearer_token(request: Request) -> str:
    scheme, _, token = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Credenciales de autenticación no válidas")
    return token


def _validate_product(request: Request, id_producto: int) -> None:
    try:
        product = request_service(
            "catalogo",
            "GET",
            f"/products/{id_producto}",
            bearer_token=_bearer_token(request),
        )
    except RemoteServiceError as error:
        if error.status_code == 404:
            raise HTTPException(status_code=422, detail="El producto indicado no existe") from None
        raise HTTPException(
            status_code=503 if error.status_code == 503 else 502,
            detail="No fue posible validar el producto en Catálogo",
        ) from None
    if (
        not isinstance(product, dict)
        or product.get("id_producto") != id_producto
        or product.get("estado") != "activo"
    ):
        raise HTTPException(status_code=422, detail="El producto no está disponible para compra")


@router.get("/suppliers", response_model=list[SupplierResponse])
def read_suppliers(
    estado: Annotated[ResourceState | None, Query()] = None,
    q: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=100_000)] = 0,
    db: Session = Depends(get_compras_db),
) -> list[SupplierResponse]:
    rows = list_suppliers(
        db,
        estado=estado,
        search=q,
        limit=limit,
        offset=offset,
    )
    return [SupplierResponse.model_validate(row) for row in rows]


@router.get("/suppliers/{id_proveedor}", response_model=SupplierResponse)
def read_supplier(
    id_proveedor: Annotated[int, Path(gt=0)],
    db: Session = Depends(get_compras_db),
) -> SupplierResponse:
    row = get_supplier(db, id_proveedor)
    if row is None:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    return SupplierResponse.model_validate(row)


@router.post(
    "/suppliers",
    response_model=SupplierResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_supplier(
    data: SupplierCreate,
    request: Request,
    db: Session = Depends(get_compras_db),
) -> SupplierResponse:
    try:
        row = create_supplier(db, data.model_dump())
        _commit_or_conflict(db)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="La identificación o razón social ya existe",
        ) from None
    set_audit_details(
        request,
        object_type="compras.proveedores",
        object_id=row["id_proveedor"],
        after=row,
    )
    return SupplierResponse.model_validate(row)


@router.patch("/suppliers/{id_proveedor}", response_model=SupplierResponse)
def edit_supplier(
    id_proveedor: Annotated[int, Path(gt=0)],
    data: SupplierUpdate,
    request: Request,
    db: Session = Depends(get_compras_db),
) -> SupplierResponse:
    before = get_supplier(db, id_proveedor)
    values = data.model_dump(exclude_unset=True)
    try:
        row = update_supplier(db, id_proveedor, values)
        if row is None:
            db.rollback()
            raise HTTPException(status_code=404, detail="Proveedor no encontrado")
        _commit_or_conflict(db)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="La identificación o razón social ya existe",
        ) from None
    set_audit_details(
        request,
        object_type="compras.proveedores",
        object_id=id_proveedor,
        before=before,
        after=row,
    )
    return SupplierResponse.model_validate(row)


@router.delete("/suppliers/{id_proveedor}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_supplier(
    id_proveedor: Annotated[int, Path(gt=0)],
    request: Request,
    db: Session = Depends(get_compras_db),
) -> None:
    before = get_supplier(db, id_proveedor)
    row = update_supplier(db, id_proveedor, {"estado": "inactivo"})
    if row is None:
        db.rollback()
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    _commit_or_conflict(db)
    set_audit_details(
        request,
        object_type="compras.proveedores",
        object_id=id_proveedor,
        before=before,
        after=row,
    )


@router.get("/product-suppliers", response_model=list[ProductSupplierResponse])
def read_product_suppliers(
    id_producto: Annotated[int | None, Query(gt=0)] = None,
    id_proveedor: Annotated[int | None, Query(gt=0)] = None,
    estado: Annotated[ResourceState | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=100_000)] = 0,
    db: Session = Depends(get_compras_db),
) -> list[ProductSupplierResponse]:
    rows = list_product_suppliers(
        db,
        id_producto=id_producto,
        id_proveedor=id_proveedor,
        estado=estado,
        limit=limit,
        offset=offset,
    )
    return [ProductSupplierResponse.model_validate(row) for row in rows]


@router.put(
    "/product-suppliers/{id_producto}/{id_proveedor}",
    response_model=ProductSupplierResponse,
)
def save_product_supplier(
    id_producto: Annotated[int, Path(gt=0)],
    id_proveedor: Annotated[int, Path(gt=0)],
    data: ProductSupplierInput,
    request: Request,
    db: Session = Depends(get_compras_db),
) -> ProductSupplierResponse:
    before = get_product_supplier(
        db,
        id_producto=id_producto,
        id_proveedor=id_proveedor,
    )
    supplier = get_supplier(db, id_proveedor)
    if supplier is None:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    if supplier["estado"] != "activo":
        raise HTTPException(status_code=409, detail="El proveedor está inactivo")
    _validate_product(request, id_producto)
    try:
        row = upsert_product_supplier(
            db,
            id_producto=id_producto,
            id_proveedor=id_proveedor,
            values=data.model_dump(),
        )
        _commit_or_conflict(db)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="No fue posible guardar la relación") from None
    set_audit_details(
        request,
        object_type="compras.producto_proveedor",
        object_id=f"{id_producto}:{id_proveedor}",
        before=before,
        after=row,
    )
    return ProductSupplierResponse.model_validate(row)


@router.delete(
    "/product-suppliers/{id_producto}/{id_proveedor}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def deactivate_product_supplier_link(
    id_producto: Annotated[int, Path(gt=0)],
    id_proveedor: Annotated[int, Path(gt=0)],
    request: Request,
    db: Session = Depends(get_compras_db),
) -> None:
    before = get_product_supplier(
        db,
        id_producto=id_producto,
        id_proveedor=id_proveedor,
    )
    row = deactivate_product_supplier(
        db,
        id_producto=id_producto,
        id_proveedor=id_proveedor,
    )
    if row is None:
        db.rollback()
        raise HTTPException(status_code=404, detail="Relación producto-proveedor no encontrada")
    _commit_or_conflict(db)
    set_audit_details(
        request,
        object_type="compras.producto_proveedor",
        object_id=f"{id_producto}:{id_proveedor}",
        before=before,
        after=row,
    )
