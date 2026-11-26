
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.services.inventarios.dependencies import get_inventarios_db
from app.services.inventarios.repositories import (
    adjust_inventory,
    dispatch_sales_order,
    list_inventory,
    register_sales_return,
    update_stock_minimum,
)
from app.services.inventarios.schemas import (
    InventoryResponse,
    SalesDispatchCreate,
    SalesReturnCreate,
    StockAdjustment,
    StockMinimumUpdate,
)
from app.shared.audit import set_audit_details
from app.shared.clients import request_service
from app.shared.exceptions import RemoteServiceError
from app.shared.transactions import set_local_transaction_timeouts


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
    require_active: bool = False,
) -> dict:
    authorization = request.headers.get("authorization", "")
    scheme, _, bearer_token = authorization.partition(" ")

    if scheme.lower() != "bearer" or not bearer_token:
        raise HTTPException(
            status_code=401,
            detail="Credenciales no válidas",
        )

    try:
        resource = request_service(
            service,
            "GET",
            path,
            bearer_token=bearer_token,
        )
    except RemoteServiceError as error:
        if error.status_code == 404:
            raise HTTPException(
                status_code=422,
                detail="La referencia indicada no existe",
            ) from None

        raise HTTPException(
            status_code=503 if error.status_code == 503 else 502,
            detail=f"No fue posible validar la referencia en {service}",
        ) from None

    if not isinstance(resource, dict) or resource.get(id_field) != expected_id:
        raise HTTPException(
            status_code=502,
            detail=f"Respuesta inválida de {service}",
        )

    if require_active and resource.get("estado") != "activo":
        raise HTTPException(
            status_code=422,
            detail=f"La referencia no está activa en {service}",
        )

    return resource


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

    return [
        InventoryResponse.model_validate(row)
        for row in rows
    ]


@router.post(
    "/adjustments",
    response_model=InventoryResponse,
    status_code=status.HTTP_200_OK,
)
def set_stock_quantity(
    data: StockAdjustment,
    request: Request,
    db: Session = Depends(get_inventarios_db),
) -> InventoryResponse:
    _validate_remote_resource(
        request,
        "catalogo",
        f"/products/{data.id_producto}",
        data.id_producto,
        "id_producto",
        require_active=True,
    )

    warehouse = _validate_remote_resource(
        request,
        "organizacion",
        f"/warehouses/{data.id_almacen}",
        data.id_almacen,
        "id_almacen",
        require_active=True,
    )

    before_rows = list_inventory(
        db,
        id_producto=data.id_producto,
        id_sede=warehouse["id_sede"],
        id_almacen=data.id_almacen,
        below_minimum=None,
        limit=1,
        offset=0,
    )

    try:
        set_local_transaction_timeouts(db)

        row = adjust_inventory(
            db,
            id_almacen=data.id_almacen,
            id_producto=data.id_producto,
            id_sede=warehouse["id_sede"],
            existencia_objetivo=data.existencia_objetivo,
        )

        db.commit()

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="No fue posible ajustar las existencias",
        ) from None

    set_audit_details(
        request,
        object_type="inventarios.inventarios",
        object_id=f"{data.id_almacen}:{data.id_producto}",
        before=before_rows[0] if before_rows else None,
        after=row,
        details={"operacion": "ajuste_existencias"},
    )

    return InventoryResponse.model_validate(row)


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

    before_rows = list_inventory(
        db,
        id_producto=data.id_producto,
        id_sede=None,
        id_almacen=data.id_almacen,
        below_minimum=None,
        limit=1,
        offset=0,
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
            raise HTTPException(
                status_code=404,
                detail="Registro de inventario no encontrado",
            )

        db.commit()

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="No fue posible actualizar el nivel mínimo",
        ) from None

    set_audit_details(
        request,
        object_type="inventarios.inventarios",
        object_id=f"{data.id_almacen}:{data.id_producto}",
        before=before_rows[0] if before_rows else None,
        after=row,
        details={"operacion": "actualizar_stock_minimo"},
    )

    return InventoryResponse.model_validate(row)


@router.post(
    "/sales-dispatches",
    status_code=status.HTTP_200_OK,
)
def dispatch_paid_order(
    data: SalesDispatchCreate,
    request: Request,
    db: Session = Depends(get_inventarios_db),
) -> dict:
    warehouse = _validate_remote_resource(
        request,
        "organizacion",
        f"/warehouses/{data.id_almacen}",
        data.id_almacen,
        "id_almacen",
        require_active=True,
    )

    if warehouse.get("id_sede") != data.id_sede:
        raise HTTPException(
            status_code=422,
            detail="El almacén no pertenece a la sede indicada",
        )

    try:
        set_local_transaction_timeouts(db)

        result = dispatch_sales_order(
            db,
            id_pedido=data.id_pedido,
            id_sede=data.id_sede,
            id_almacen=data.id_almacen,
            products=[
                {
                    "id_producto": item.id_producto,
                    "cantidad": item.cantidad,
                }
                for item in data.productos
            ],
        )

        db.commit()

    except ValueError as error:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail=str(error),
        ) from None

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="No fue posible registrar el despacho del pedido",
        ) from None

    except Exception:
        db.rollback()
        raise

    set_audit_details(
        request,
        object_type="inventarios.despachos_venta",
        object_id=data.id_pedido,
        after=result,
        details={
            "operacion": "despacho_venta",
            "ya_despachado": result["already_dispatched"],
        },
    )

    return result


@router.post(
    "/sales-returns",
    status_code=status.HTTP_200_OK,
)
def register_returned_order_stock(
    data: SalesReturnCreate,
    request: Request,
    db: Session = Depends(get_inventarios_db),
) -> dict:
    warehouse = _validate_remote_resource(
        request,
        "organizacion",
        f"/warehouses/{data.id_almacen}",
        data.id_almacen,
        "id_almacen",
    )
    if warehouse.get("id_sede") != data.id_sede:
        raise HTTPException(
            status_code=422,
            detail="El almacén no pertenece a la sede indicada",
        )

    try:
        set_local_transaction_timeouts(db)
        result = register_sales_return(
            db,
            id_devolucion=data.id_devolucion,
            id_pedido=data.id_pedido,
            id_sede=data.id_sede,
            id_almacen=data.id_almacen,
            products=[
                {
                    "id_producto": item.id_producto,
                    "cantidad": item.cantidad,
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
        raise HTTPException(
            status_code=409,
            detail="No fue posible registrar el reintegro de la devolución",
        ) from None
    except Exception:
        db.rollback()
        raise

    set_audit_details(
        request,
        object_type="inventarios.devoluciones_venta",
        object_id=data.id_devolucion,
        after=result,
        details={
            "operacion": "reintegro_devolucion_venta",
            "ya_procesada": result["already_returned"],
        },
    )

    return result


__all__ = ["router"]
