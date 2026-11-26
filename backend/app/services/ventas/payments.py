from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.services.ventas.dependencies import get_ventas_db
from app.services.ventas.repositories import (
    create_payment,
    get_order,
    list_payments,
    lock_order,
    mark_order_completed,
    order_balance,
)
from app.services.ventas.schemas import (
    OrderBalanceResponse,
    PaymentCreate,
    PaymentResponse,
)
from app.shared.transactions import set_local_transaction_timeouts
from app.shared.audit import set_audit_details

router = APIRouter(prefix="/orders", tags=["Pagos"])


@router.post(
    "/{id_pedido}/payments",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_order_payment(
    id_pedido: Annotated[int, Path(gt=0)],
    data: PaymentCreate,
    request: Request,
    db: Session = Depends(get_ventas_db),
) -> PaymentResponse:
    try:
        set_local_transaction_timeouts(db)
        order = lock_order(db, id_pedido)
        if order is None:
            db.rollback()
            raise HTTPException(status_code=404, detail="Pedido no encontrado")
        if order["estado"] not in ("pendiente", "completado"):
            db.rollback()
            raise HTTPException(status_code=409, detail="El pedido no admite pagos")
        balance = order_balance(db, id_pedido, order["total_registrado"])
        before = {
            "estado_pedido": order["estado"],
            "saldo_pendiente": balance,
        }
        if data.valor > balance:
            db.rollback()
            raise HTTPException(status_code=409, detail="El pago supera el saldo pendiente")
        row = create_payment(
            db,
            id_pedido=id_pedido,
            valor=data.valor,
            medio_pago=data.medio_pago,
        )
        if data.valor == balance:
            mark_order_completed(db, order)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="No fue posible registrar el pago") from None
    set_audit_details(
        request,
        object_type="ventas.pagos",
        object_id=row["id_pago"],
        before=before,
        after={
            "id_pago": row["id_pago"],
            "id_pedido": id_pedido,
            "estado_pedido": "completado" if data.valor == before["saldo_pendiente"] else order["estado"],
            "saldo_pendiente": max(before["saldo_pendiente"] - data.valor, 0),
            "valor": row["valor"],
            "medio_pago": row["medio_pago"],
        },
    )
    return PaymentResponse.model_validate(row)


@router.get("/{id_pedido}/payments", response_model=list[PaymentResponse])
def read_order_payments(
    id_pedido: Annotated[int, Path(gt=0)],
    db: Session = Depends(get_ventas_db),
) -> list[PaymentResponse]:
    if get_order(db, id_pedido) is None:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    rows = list_payments(db, id_pedido)
    return [PaymentResponse.model_validate(row) for row in rows]


@router.get("/{id_pedido}/balance", response_model=OrderBalanceResponse)
def read_order_balance(
    id_pedido: Annotated[int, Path(gt=0)],
    db: Session = Depends(get_ventas_db),
) -> OrderBalanceResponse:
    order = get_order(db, id_pedido)
    if order is None:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    balance = order_balance(db, id_pedido, order["total_registrado"])
    return OrderBalanceResponse(
        id_pedido=id_pedido,
        total_registrado=order["total_registrado"],
        total_pagado=order["total_registrado"] - balance,
        saldo_pendiente=balance,
    )
