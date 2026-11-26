from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.services.ventas.dependencies import get_ventas_db
from app.services.ventas.repositories import (
    create_return,
    get_order,
    get_return,
    lock_order,
    list_return_details,
    list_returns,
    resolve_return,
)
from app.services.ventas.schemas import (
    ReturnCreate,
    ReturnDetailResponse,
    ReturnResponse,
)
from app.shared.clients import request_service
from app.shared.exceptions import RemoteServiceError
from app.shared.transactions import set_local_transaction_timeouts
from app.shared.audit import set_audit_details

router = APIRouter(tags=["Devoluciones"])


def _validate_product(request: Request, id_producto: int) -> None:
    scheme, _, bearer_token = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not bearer_token:
        raise HTTPException(status_code=401, detail="Credenciales no válidas")
    try:
        product = request_service(
            "catalogo",
            "GET",
            f"/products/{id_producto}",
            bearer_token=bearer_token,
        )
    except RemoteServiceError as error:
        if error.status_code == 404:
            raise HTTPException(status_code=422, detail="El producto indicado no existe") from None
        raise HTTPException(
            status_code=503 if error.status_code == 503 else 502,
            detail="No fue posible validar el producto en Catálogo",
        ) from None
    if not isinstance(product, dict) or product.get("id_producto") != id_producto:
        raise HTTPException(status_code=502, detail="Respuesta inválida de Catálogo")


@router.post(
    "/orders/{id_pedido}/returns",
    response_model=ReturnResponse,
    status_code=status.HTTP_201_CREATED,
)
def request_return(
    id_pedido: Annotated[int, Path(gt=0)],
    data: ReturnCreate,
    request: Request,
    db: Session = Depends(get_ventas_db),
) -> ReturnResponse:
    for item in data.productos:
        _validate_product(request, item.id_producto)
    try:
        set_local_transaction_timeouts(db)
        order = lock_order(db, id_pedido)
        if order is None:
            db.rollback()
            raise HTTPException(status_code=404, detail="Pedido no encontrado")
        if order["estado"] not in ("completado", "devolucion"):
            db.rollback()
            raise HTTPException(status_code=409, detail="El pedido no admite devoluciones")
        row = create_return(
            db,
            id_pedido=id_pedido,
            motivo=data.motivo,
            products=[
                {
                    "id_producto": item.id_producto,
                    "cantidad": item.cantidad,
                    "condicion_producto": item.condicion_producto,
                }
                for item in data.productos
            ],
        )
        db.commit()
    except ValueError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(error)) from None
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="No fue posible solicitar la devolución") from None
    set_audit_details(
        request,
        object_type="ventas.devoluciones",
        object_id=row["id_devolucion"],
        before={"id_pedido": id_pedido, "estado_pedido": order["estado"]},
        after={
            "id_devolucion": row["id_devolucion"],
            "id_pedido": row["id_pedido"],
            "estado": row["estado"],
        },
        details={
            "productos": [
                {
                    "id_producto": item.id_producto,
                    "cantidad": item.cantidad,
                    "condicion_producto": item.condicion_producto,
                }
                for item in data.productos
            ],
        },
    )
    return ReturnResponse.model_validate(row)


@router.get(
    "/orders/{id_pedido}/returns",
    response_model=list[ReturnResponse],
)
def read_order_returns(
    id_pedido: Annotated[int, Path(gt=0)],
    db: Session = Depends(get_ventas_db),
) -> list[ReturnResponse]:
    if get_order(db, id_pedido) is None:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    rows = list_returns(db, id_pedido)
    return [ReturnResponse.model_validate(row) for row in rows]


@router.get(
    "/returns/{id_devolucion}",
    response_model=ReturnResponse,
)
def read_return(
    id_devolucion: Annotated[int, Path(gt=0)],
    db: Session = Depends(get_ventas_db),
) -> ReturnResponse:
    row = get_return(db, id_devolucion)
    if row is None:
        raise HTTPException(status_code=404, detail="Devolución no encontrada")
    return ReturnResponse.model_validate(row)


@router.get(
    "/returns/{id_devolucion}/details",
    response_model=list[ReturnDetailResponse],
)
def read_return_details(
    id_devolucion: Annotated[int, Path(gt=0)],
    db: Session = Depends(get_ventas_db),
) -> list[ReturnDetailResponse]:
    if get_return(db, id_devolucion) is None:
        raise HTTPException(status_code=404, detail="Devolución no encontrada")
    rows = list_return_details(db, id_devolucion)
    return [ReturnDetailResponse.model_validate(row) for row in rows]


@router.post("/returns/{id_devolucion}/approve", response_model=ReturnResponse)
def approve_return(
    id_devolucion: Annotated[int, Path(gt=0)],
    request: Request,
    db: Session = Depends(get_ventas_db),
) -> ReturnResponse:
    return _resolve_return(id_devolucion, approve=True, request=request, db=db)


@router.post("/returns/{id_devolucion}/reject", response_model=ReturnResponse)
def reject_return(
    id_devolucion: Annotated[int, Path(gt=0)],
    request: Request,
    db: Session = Depends(get_ventas_db),
) -> ReturnResponse:
    return _resolve_return(id_devolucion, approve=False, request=request, db=db)


def _resolve_return(
    id_devolucion: int,
    *,
    approve: bool,
    request: Request,
    db: Session,
) -> ReturnResponse:
    before = get_return(db, id_devolucion)
    try:
        set_local_transaction_timeouts(db)
        row = resolve_return(db, id_devolucion=id_devolucion, approve=approve)
        if row is None:
            db.rollback()
            raise HTTPException(status_code=404, detail="Devolución no encontrada")

        if approve:
            order = get_order(db, row["id_pedido"])
            if order is None:
                raise HTTPException(
                    status_code=409,
                    detail="No fue posible encontrar el pedido de la devolución",
                )
            products = [
                {
                    "id_producto": item["id_producto"],
                    "cantidad": item["cantidad"],
                }
                for item in list_return_details(db, id_devolucion)
                if item["condicion_producto"] == "buen_estado"
            ]
            authorization = request.headers.get("authorization", "")
            scheme, _, bearer_token = authorization.partition(" ")
            if scheme.lower() != "bearer" or not bearer_token:
                raise HTTPException(status_code=401, detail="Credenciales no válidas")
            try:
                request_service(
                    "inventarios",
                    "POST",
                    "/stock/sales-returns",
                    bearer_token=bearer_token,
                    json_body={
                        "id_devolucion": id_devolucion,
                        "id_pedido": row["id_pedido"],
                        "id_sede": order["id_sede"],
                        "id_almacen": order["id_almacen"],
                        "productos": products,
                    },
                )
            except RemoteServiceError as error:
                if error.status_code in (409, 422):
                    raise HTTPException(
                        status_code=409,
                        detail=(
                            "No fue posible aprobar la devolución porque "
                            f"Inventarios rechazó el reintegro: {error}"
                        ),
                    ) from None
                raise HTTPException(
                    status_code=503,
                    detail="No fue posible confirmar el reintegro en Inventarios",
                ) from None

        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except ValueError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(error)) from None
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="No fue posible resolver la devolución") from None
    except Exception:
        db.rollback()
        raise
    set_audit_details(
        request,
        object_type="ventas.devoluciones",
        object_id=id_devolucion,
        before=before,
        after=row,
        details={"operacion": "aprobacion" if approve else "rechazo"},
    )
    return ReturnResponse.model_validate(row)
