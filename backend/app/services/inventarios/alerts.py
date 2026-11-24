from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.services.inventarios.dependencies import get_inventarios_db
from app.services.inventarios.repositories import list_inventory
from app.services.inventarios.schemas import InventoryResponse

router = APIRouter(
    prefix="/stock",
    tags=["Alertas de inventario"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/alerts", response_model=list[InventoryResponse])
def read_low_stock_alerts(
    id_sede: Annotated[int | None, Query(gt=0)] = None,
    id_almacen: Annotated[int | None, Query(gt=0)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=100_000)] = 0,
    db: Session = Depends(get_inventarios_db),
) -> list[InventoryResponse]:
    rows = list_inventory(
        db,
        id_producto=None,
        id_sede=id_sede,
        id_almacen=id_almacen,
        below_minimum=True,
        limit=limit,
        offset=offset,
    )
    return [InventoryResponse.model_validate(row) for row in rows]
