from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session

from app.services.ventas.dependencies import get_ventas_db
from app.services.ventas.repositories import (
    get_order,
    get_return,
    list_return_details,
    list_returns,
)
from app.services.ventas.schemas import ReturnDetailResponse, ReturnResponse

router = APIRouter(tags=["Devoluciones"])


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
