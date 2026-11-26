from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.services.ventas.dependencies import get_ventas_db
from app.services.ventas.repositories import (
    create_customer,
    get_customer,
    list_customers,
    update_customer,
)
from app.services.ventas.schemas import CustomerCreate, CustomerResponse, CustomerUpdate, SalesState
from app.shared.audit import set_audit_details

router = APIRouter(prefix="/customers", tags=["Clientes"])


def _commit_or_conflict(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="El número de documento ya existe o hay un conflicto de datos",
        ) from None


@router.get("", response_model=list[CustomerResponse])
def read_customers(
    estado: Annotated[SalesState | None, Query()] = None,
    num_documento: Annotated[str | None, Query(min_length=1, max_length=20)] = None,
    q: Annotated[str | None, Query(min_length=1, max_length=120)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=100_000)] = 0,
    db: Session = Depends(get_ventas_db),
) -> list[CustomerResponse]:
    rows = list_customers(
        db,
        estado=estado,
        num_documento=num_documento,
        search=q,
        limit=limit,
        offset=offset,
    )
    return [CustomerResponse.model_validate(row) for row in rows]


@router.get("/{id_cliente}", response_model=CustomerResponse)
def read_customer(
    id_cliente: Annotated[int, Path(gt=0)],
    db: Session = Depends(get_ventas_db),
) -> CustomerResponse:
    row = get_customer(db, id_cliente)
    if row is None:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return CustomerResponse.model_validate(row)


@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def add_customer(
    data: CustomerCreate,
    request: Request,
    db: Session = Depends(get_ventas_db),
) -> CustomerResponse:
    try:
        row = create_customer(db, data.model_dump())
        _commit_or_conflict(db)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="El número de documento ya existe") from None
    set_audit_details(
        request,
        object_type="ventas.clientes",
        object_id=row["id_cliente"],
        after=row,
    )
    return CustomerResponse.model_validate(row)


@router.patch("/{id_cliente}", response_model=CustomerResponse)
def edit_customer(
    id_cliente: Annotated[int, Path(gt=0)],
    data: CustomerUpdate,
    request: Request,
    db: Session = Depends(get_ventas_db),
) -> CustomerResponse:
    before = get_customer(db, id_cliente)
    values = data.model_dump(exclude_unset=True)
    try:
        row = update_customer(db, id_cliente, values)
        if row is None:
            db.rollback()
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        _commit_or_conflict(db)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="El número de documento ya existe") from None
    set_audit_details(
        request,
        object_type="ventas.clientes",
        object_id=id_cliente,
        before=before,
        after=row,
    )
    return CustomerResponse.model_validate(row)


@router.delete("/{id_cliente}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_customer(
    id_cliente: Annotated[int, Path(gt=0)],
    request: Request,
    db: Session = Depends(get_ventas_db),
) -> None:
    before = get_customer(db, id_cliente)
    row = update_customer(db, id_cliente, {"estado": "inactivo"})
    if row is None:
        db.rollback()
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    _commit_or_conflict(db)
    set_audit_details(
        request,
        object_type="ventas.clientes",
        object_id=id_cliente,
        before=before,
        after=row,
    )
