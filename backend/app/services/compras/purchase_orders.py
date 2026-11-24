from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.services.compras.dependencies import get_compras_db
from app.services.compras.repositories import (
    cancel_purchase_order,
    get_purchase_order,
    list_purchase_order_details,
    list_purchase_orders,
)
from app.services.compras.schemas import (
    PurchaseOrderDetailResponse,
    PurchaseOrderResponse,
    PurchaseState,
)

router = APIRouter(prefix="/purchase-orders", tags=["Órdenes de compra"])


@router.get("", response_model=list[PurchaseOrderResponse])
def read_purchase_orders(
    id_proveedor: Annotated[int | None, Query(gt=0)] = None,
    id_almacen_destino: Annotated[int | None, Query(gt=0)] = None,
    id_empleado_creador: Annotated[int | None, Query(gt=0)] = None,
    estado: Annotated[PurchaseState | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=100_000)] = 0,
    db: Session = Depends(get_compras_db),
) -> list[PurchaseOrderResponse]:
    rows = list_purchase_orders(
        db,
        id_proveedor=id_proveedor,
        id_almacen_destino=id_almacen_destino,
        id_empleado_creador=id_empleado_creador,
        estado=estado,
        limit=limit,
        offset=offset,
    )
    return [PurchaseOrderResponse.model_validate(row) for row in rows]


@router.get("/{id_orden_compra}", response_model=PurchaseOrderResponse)
def read_purchase_order(
    id_orden_compra: Annotated[int, Path(gt=0)],
    db: Session = Depends(get_compras_db),
) -> PurchaseOrderResponse:
    row = get_purchase_order(db, id_orden_compra)
    if row is None:
        raise HTTPException(status_code=404, detail="Orden de compra no encontrada")
    return PurchaseOrderResponse.model_validate(row)


@router.get(
    "/{id_orden_compra}/details",
    response_model=list[PurchaseOrderDetailResponse],
)
def read_purchase_order_details(
    id_orden_compra: Annotated[int, Path(gt=0)],
    db: Session = Depends(get_compras_db),
) -> list[PurchaseOrderDetailResponse]:
    if get_purchase_order(db, id_orden_compra) is None:
        raise HTTPException(status_code=404, detail="Orden de compra no encontrada")
    rows = list_purchase_order_details(db, id_orden_compra)
    return [PurchaseOrderDetailResponse.model_validate(row) for row in rows]


@router.post("/{id_orden_compra}/cancel", response_model=PurchaseOrderResponse)
def cancel_order(
    id_orden_compra: Annotated[int, Path(gt=0)],
    db: Session = Depends(get_compras_db),
) -> PurchaseOrderResponse:
    try:
        row = cancel_purchase_order(db, id_orden_compra)
        if row is None:
            existing = get_purchase_order(db, id_orden_compra)
            db.rollback()
            if existing is None:
                raise HTTPException(status_code=404, detail="Orden de compra no encontrada")
            raise HTTPException(
                status_code=409,
                detail="Solo se pueden cancelar órdenes pendientes",
            )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="No fue posible cancelar la orden") from None
    return PurchaseOrderResponse.model_validate(row)
