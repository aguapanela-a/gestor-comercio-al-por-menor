from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.services.inventarios.dependencies import get_inventarios_db
from app.services.inventarios.repositories import list_inventory, update_stock_minimum
from app.services.inventarios.schemas import InventoryResponse, StockMinimumUpdate
from app.shared.clients import request_service
from app.shared.exceptions import RemoteServiceError

router = APIRouter(
    prefix="/stock",
    tags=["Inventario"],
    dependencies=[Depends(get_current_user)],
)


def _validate_remote_resource(
    request: Request,
    service: str,
    path: str,
    expected_id: int,
    id_field: str,
) -> None:
    authorization = request.headers.get("authorization", "")
    scheme, _, bearer_token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not bearer_token:
        raise HTTPException(status_code=401, detail="Credenciales no válidas")
    try:
        resource = request_service(
            service,
            "GET",
            path,
            bearer_token=bearer_token,
        )
    except RemoteServiceError as error:
        if error.status_code == 404:
            raise HTTPException(status_code=422, detail="La referencia indicada no existe") from None
        raise HTTPException(
            status_code=503 if error.status_code == 503 else 502,
            detail=f"No fue posible validar la referencia en {service}",
        ) from None
    if not isinstance(resource, dict) or resource.get(id_field) != expected_id:
        raise HTTPException(status_code=502, detail=f"Respuesta inválida de {service}")


@router.get("", response_model=list[InventoryResponse])
def read_stock(
    id_producto: Annotated[int | None, Query(gt=0)] = None,
    id_sede: Annotated[int | None, Query(gt=0)] = None,
    id_almacen: Annotated[int | None, Query(gt=0)] = None,
    bajo_minimo: bool | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=100_000)] = 0,
    db: Session = Depends(get_inventarios_db),
) -> list[InventoryResponse]:
    rows = list_inventory(
        db,
        id_producto=id_producto,
        id_sede=id_sede,
        id_almacen=id_almacen,
        below_minimum=bajo_minimo,
        limit=limit,
        offset=offset,
    )
    return [InventoryResponse.model_validate(row) for row in rows]


@router.patch("/minimum", response_model=InventoryResponse)
def set_stock_minimum(
    data: StockMinimumUpdate,
    request: Request,
    db: Session = Depends(get_inventarios_db),
) -> InventoryResponse:
    _validate_remote_resource(
        request,
        "catalogo",
        f"/products/{data.id_producto}",
        data.id_producto,
        "id_producto",
    )
    _validate_remote_resource(
        request,
        "organizacion",
        f"/warehouses/{data.id_almacen}",
        data.id_almacen,
        "id_almacen",
    )
    try:
        row = update_stock_minimum(
            db,
            id_almacen=data.id_almacen,
            id_producto=data.id_producto,
            stock_minimo=data.stock_minimo,
        )
        if row is None:
            db.rollback()
            raise HTTPException(status_code=404, detail="Registro de inventario no encontrado")
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="No fue posible actualizar el nivel mínimo") from None
    return InventoryResponse.model_validate(row)


__all__ = ["router"]
