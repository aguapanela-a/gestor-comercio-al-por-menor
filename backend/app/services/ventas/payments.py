
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.services.ventas.dependencies import get_ventas_db
from app.services.ventas.repositories import (
    create_payment,
    get_order,
    list_order_details,
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
from app.shared.audit import set_audit_details
from app.shared.clients import request_service
from app.shared.exceptions import RemoteServiceError
from app.shared.transactions import set_local_transaction_timeouts


router = APIRouter(prefix="/orders", tags=["Pagos"])


def _get_bearer_token(request: Request) -> str:
    authorization = request.headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")

    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=401,
            detail="Credenciales no válidas",
        )

    return token


def _dispatch_order_to_inventory(
    request: Request,
    order: dict,
    id_pedido: int,
    details: list[dict],
) -> dict:
    payload = {
        "id_pedido": id_pedido,
        "id_sede": order["id_sede"],
        "id_almacen": order["id_almacen"],
        "productos": [
            {
                "id_producto": item["id_producto"],
                "cantidad": item["cantidad"],
            }
            for item in details
        ],
    }

    try:
        return request_service(
            "inventarios",
            "POST",
            "/stock/sales-dispatches",
            bearer_token=_get_bearer_token(request),
            json_body=payload,
        )

    except RemoteServiceError as error:
        if error.status_code in (409, 422):
            raise HTTPException(
                status_code=409,
                detail=(
                    "No fue posible completar el pago porque "
                    f"Inventarios rechazó el despacho: {error}"
                ),
            ) from None

        raise HTTPException(
            status_code=503,
            detail="No fue posible confirmar el despacho en Inventarios",
        ) from None


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
            raise HTTPException(
                status_code=404,
                detail="Pedido no encontrado",
            )

        if order["estado"] not in ("pendiente", "completado"):
            raise HTTPException(
                status_code=409,
                detail="El pedido no admite pagos",
            )

        balance = order_balance(
            db,
            id_pedido,
            order["total_registrado"],
        )

        before = {
            "estado_pedido": order["estado"],
            "saldo_pendiente": balance,
        }

        if data.valor > balance:
            raise HTTPException(
                status_code=409,
                detail="El pago supera el saldo pendiente",
            )

        if balance <= 0:
            raise HTTPException(
                status_code=409,
                detail="El pedido ya está completamente pagado",
            )

        row = create_payment(
            db,
            id_pedido=id_pedido,
            valor=data.valor,
            medio_pago=data.medio_pago,
        )

        if data.valor == balance:
            details = list_order_details(db, id_pedido)

            if not details:
                raise HTTPException(
                    status_code=409,
                    detail="El pedido no tiene productos para despachar",
                )

            _dispatch_order_to_inventory(
                request,
                order,
                id_pedido,
                details,
            )

            mark_order_completed(db, order)

        db.commit()

    except HTTPException:
        db.rollback()
        raise

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="No fue posible registrar el pago",
        ) from None

    except Exception:
        db.rollback()
        raise

    set_audit_details(
        request,
        object_type="ventas.pagos",
        object_id=row["id_pago"],
        before=before,
        after={
            "id_pago": row["id_pago"],
            "id_pedido": id_pedido,
            "estado_pedido": (
                "completado"
                if data.valor == before["saldo_pendiente"]
                else order["estado"]
            ),
            "saldo_pendiente": max(
                before["saldo_pendiente"] - data.valor,
                0,
            ),
            "valor": row["valor"],
            "medio_pago": row["medio_pago"],
        },
    )

    return PaymentResponse.model_validate(row)


@router.get(
    "/{id_pedido}/payments",
    response_model=list[PaymentResponse],
)
def read_order_payments(
    id_pedido: Annotated[int, Path(gt=0)],
    db: Session = Depends(get_ventas_db),
) -> list[PaymentResponse]:
    if get_order(db, id_pedido) is None:
        raise HTTPException(
            status_code=404,
            detail="Pedido no encontrado",
        )

    rows = list_payments(db, id_pedido)

    return [
        PaymentResponse.model_validate(row)
        for row in rows
    ]


@router.get(
    "/{id_pedido}/balance",
    response_model=OrderBalanceResponse,
)
def read_order_balance(
    id_pedido: Annotated[int, Path(gt=0)],
    db: Session = Depends(get_ventas_db),
) -> OrderBalanceResponse:
    order = get_order(db, id_pedido)

    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Pedido no encontrado",
        )

    balance = order_balance(
        db,
        id_pedido,
        order["total_registrado"],
    )

    return OrderBalanceResponse(
        id_pedido=id_pedido,
        total_registrado=order["total_registrado"],
        total_pagado=order["total_registrado"] - balance,
        saldo_pendiente=balance,
    )
