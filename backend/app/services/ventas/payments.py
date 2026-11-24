from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session

from app.services.ventas.dependencies import get_ventas_db
from app.services.ventas.repositories import get_order, list_payments
from app.services.ventas.schemas import PaymentResponse

router = APIRouter(prefix="/orders", tags=["Pagos"])


@router.get("/{id_pedido}/payments", response_model=list[PaymentResponse])
def read_order_payments(
    id_pedido: Annotated[int, Path(gt=0)],
    db: Session = Depends(get_ventas_db),
) -> list[PaymentResponse]:
    if get_order(db, id_pedido) is None:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    rows = list_payments(db, id_pedido)
    return [PaymentResponse.model_validate(row) for row in rows]
