from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from app.services.ventas.dependencies import get_ventas_db
from app.services.ventas.repositories import get_order, list_order_details, list_orders
from app.services.ventas.schemas import OrderDetailResponse, OrderResponse, OrderState

router = APIRouter(prefix="/orders", tags=["Pedidos"])


@router.get("", response_model=list[OrderResponse])
def read_orders(
    id_sede: Annotated[int | None, Query(ge=1, le=4)] = None,
    id_almacen: Annotated[int | None, Query(gt=0)] = None,
    id_cliente: Annotated[int | None, Query(gt=0)] = None,
    id_empleado: Annotated[int | None, Query(gt=0)] = None,
    estado: Annotated[OrderState | None, Query()] = None,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=100_000)] = 0,
    db: Session = Depends(get_ventas_db),
) -> list[OrderResponse]:
    if fecha_desde is not None and fecha_hasta is not None and fecha_hasta < fecha_desde:
        raise HTTPException(status_code=422, detail="El rango de fechas no es válido")
    rows = list_orders(
        db,
        id_sede=id_sede,
        id_almacen=id_almacen,
        id_cliente=id_cliente,
        id_empleado=id_empleado,
        estado=estado,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        limit=limit,
        offset=offset,
    )
    return [OrderResponse.model_validate(row) for row in rows]


@router.get("/{id_pedido}", response_model=OrderResponse)
def read_order(
    id_pedido: Annotated[int, Path(gt=0)],
    db: Session = Depends(get_ventas_db),
) -> OrderResponse:
    row = get_order(db, id_pedido)
    if row is None:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    return OrderResponse.model_validate(row)


@router.get("/{id_pedido}/details", response_model=list[OrderDetailResponse])
def read_order_details(
    id_pedido: Annotated[int, Path(gt=0)],
    db: Session = Depends(get_ventas_db),
) -> list[OrderDetailResponse]:
    if get_order(db, id_pedido) is None:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    rows = list_order_details(db, id_pedido)
    return [OrderDetailResponse.model_validate(row) for row in rows]
