from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.services.compras.dependencies import get_compras_db
from app.services.compras.repositories import (
    get_receipt,
    list_purchase_order_details,
    list_receipt_details,
    list_receipts,
    register_purchase_receipt,
)
from app.services.compras.schemas import (
    PurchaseReceiptCreate,
    PurchaseReceiptRegistrationResponse,
    ReceiptDetailResponse,
    ReceiptResponse,
    ReceiptState,
)
from app.shared.transactions import set_local_transaction_timeouts
from app.shared.audit import set_audit_details

router = APIRouter(prefix="/receipts", tags=["Recepciones"])


@router.post(
    "/purchase-orders/{id_orden_compra}",
    response_model=PurchaseReceiptRegistrationResponse,
)
def add_purchase_receipt(
    id_orden_compra: Annotated[int, Path(gt=0)],
    data: PurchaseReceiptCreate,
    request: Request,
    response: Response,
    db: Session = Depends(get_compras_db),
) -> PurchaseReceiptRegistrationResponse:
    try:
        set_local_transaction_timeouts(db)
        before = list_purchase_order_details(db, id_orden_compra)
        row = register_purchase_receipt(
            db,
            id_orden_compra=id_orden_compra,
            received_totals={
                item.id_producto: item.cantidad_total_recibida
                for item in data.productos
            },
        )
        if row is None:
            db.rollback()
            raise HTTPException(status_code=404, detail="Orden de compra no encontrada")
        db.commit()
    except ValueError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(error)) from None
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="No fue posible registrar la recepción") from None
    response.status_code = (
        status.HTTP_201_CREATED if row["cantidades_actualizadas"] else status.HTTP_200_OK
    )
    set_audit_details(
        request,
        object_type="compras.recepciones",
        object_id=row.get("id_recepcion") or id_orden_compra,
        before=before,
        after=row,
        details={
            "productos_recibidos": [
                {
                    "id_producto": item.id_producto,
                    "cantidad_total_recibida": item.cantidad_total_recibida,
                }
                for item in data.productos
            ],
        },
    )
    return PurchaseReceiptRegistrationResponse.model_validate(row)


@router.get("", response_model=list[ReceiptResponse])
def read_receipts(
    id_orden_compra: Annotated[int | None, Query(gt=0)] = None,
    estado: Annotated[ReceiptState | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=100_000)] = 0,
    db: Session = Depends(get_compras_db),
) -> list[ReceiptResponse]:
    rows = list_receipts(
        db,
        id_orden_compra=id_orden_compra,
        estado=estado,
        limit=limit,
        offset=offset,
    )
    return [ReceiptResponse.model_validate(row) for row in rows]


@router.get("/{id_recepcion}", response_model=ReceiptResponse)
def read_receipt(
    id_recepcion: Annotated[int, Path(gt=0)],
    db: Session = Depends(get_compras_db),
) -> ReceiptResponse:
    row = get_receipt(db, id_recepcion)
    if row is None:
        raise HTTPException(status_code=404, detail="Recepción no encontrada")
    return ReceiptResponse.model_validate(row)


@router.get("/{id_recepcion}/details", response_model=list[ReceiptDetailResponse])
def read_receipt_details(
    id_recepcion: Annotated[int, Path(gt=0)],
    db: Session = Depends(get_compras_db),
) -> list[ReceiptDetailResponse]:
    if get_receipt(db, id_recepcion) is None:
        raise HTTPException(status_code=404, detail="Recepción no encontrada")
    rows = list_receipt_details(db, id_recepcion)
    return [ReceiptDetailResponse.model_validate(row) for row in rows]
