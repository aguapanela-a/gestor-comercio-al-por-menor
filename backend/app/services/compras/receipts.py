from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from app.services.compras.dependencies import get_compras_db
from app.services.compras.repositories import (
    get_receipt,
    list_receipt_details,
    list_receipts,
)
from app.services.compras.schemas import (
    ReceiptDetailResponse,
    ReceiptResponse,
    ReceiptState,
)

router = APIRouter(prefix="/receipts", tags=["Recepciones"])


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
