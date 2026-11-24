from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.services.compras.dependencies import get_compras_db
from app.services.compras.repositories import (
    cancel_purchase_order,
    create_purchase_order,
    get_purchase_order,
    get_product_supplier,
    get_supplier,
    list_purchase_order_details,
    list_purchase_orders,
)
from app.services.compras.schemas import (
    PurchaseOrderCreate,
    PurchaseOrderDetailResponse,
    PurchaseOrderResponse,
    PurchaseState,
)
from app.shared.clients import request_service
from app.shared.exceptions import RemoteServiceError
from app.shared.transactions import set_local_transaction_timeouts

router = APIRouter(prefix="/purchase-orders", tags=["Órdenes de compra"])


def _bearer_token(request: Request) -> str:
    scheme, _, token = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Credenciales no válidas")
    return token


def _validate_remote_resource(
    request: Request,
    *,
    service: str,
    path: str,
    id_field: str,
    expected_id: int,
    require_active: bool = True,
) -> dict:
    try:
        resource = request_service(
            service,
            "GET",
            path,
            bearer_token=_bearer_token(request),
        )
    except RemoteServiceError as error:
        if error.status_code == 404:
            raise HTTPException(status_code=422, detail="La referencia indicada no existe") from None
        raise HTTPException(
            status_code=503 if error.status_code == 503 else 502,
            detail=f"No fue posible validar la referencia en {service}",
        ) from None
    if (
        not isinstance(resource, dict)
        or resource.get(id_field) != expected_id
        or (require_active and resource.get("estado") != "activo")
    ):
        raise HTTPException(status_code=422, detail=f"La referencia no está activa en {service}")
    return resource


@router.post("", response_model=PurchaseOrderResponse, status_code=status.HTTP_201_CREATED)
def add_purchase_order(
    data: PurchaseOrderCreate,
    request: Request,
    db: Session = Depends(get_compras_db),
) -> PurchaseOrderResponse:
    set_local_transaction_timeouts(db)
    supplier = get_supplier(db, data.id_proveedor)
    if supplier is None:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    if supplier["estado"] != "activo":
        raise HTTPException(status_code=409, detail="El proveedor está inactivo")

    _validate_remote_resource(
        request,
        service="organizacion",
        path=f"/warehouses/{data.id_almacen_destino}",
        id_field="id_almacen",
        expected_id=data.id_almacen_destino,
    )
    _validate_remote_resource(
        request,
        service="identidad",
        path=f"/employees/{data.id_empleado_creador}",
        id_field="id_empleado",
        expected_id=data.id_empleado_creador,
    )

    order_products = []
    for item in data.productos:
        _validate_remote_resource(
            request,
            service="catalogo",
            path=f"/products/{item.id_producto}",
            id_field="id_producto",
            expected_id=item.id_producto,
        )
        relation = get_product_supplier(
            db,
            id_producto=item.id_producto,
            id_proveedor=data.id_proveedor,
        )
        if relation is None or relation["estado"] != "activo":
            raise HTTPException(
                status_code=422,
                detail=f"El producto {item.id_producto} no está asociado activamente al proveedor",
            )
        order_products.append(
            {
                "id_producto": item.id_producto,
                "cantidad_solicitada": item.cantidad_solicitada,
                "costo_unitario": relation["costo_referencia"],
            }
        )

    try:
        row = create_purchase_order(
            db,
            id_proveedor=data.id_proveedor,
            id_almacen_destino=data.id_almacen_destino,
            id_empleado_creador=data.id_empleado_creador,
            fecha_estimada=data.fecha_estimada,
            products=order_products,
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="No fue posible crear la orden") from None
    return PurchaseOrderResponse.model_validate(row)


@router.get("", response_model=list[PurchaseOrderResponse])
def read_purchase_orders(
    id_proveedor: Annotated[int | None, Query(gt=0)] = None,
    id_almacen_destino: Annotated[int | None, Query(gt=0)] = None,
    id_empleado_creador: Annotated[int | None, Query(gt=0)] = None,
    estado: Annotated[PurchaseState | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=100_000)] = 0,
    db: Session = Depends(get_compras_db),
) -> list[PurchaseOrderResponse]:
    rows = list_purchase_orders(
        db,
        id_proveedor=id_proveedor,
        id_almacen_destino=id_almacen_destino,
        id_empleado_creador=id_empleado_creador,
        estado=estado,
        limit=limit,
        offset=offset,
    )
    return [PurchaseOrderResponse.model_validate(row) for row in rows]


@router.get("/{id_orden_compra}", response_model=PurchaseOrderResponse)
def read_purchase_order(
    id_orden_compra: Annotated[int, Path(gt=0)],
    db: Session = Depends(get_compras_db),
) -> PurchaseOrderResponse:
    row = get_purchase_order(db, id_orden_compra)
    if row is None:
        raise HTTPException(status_code=404, detail="Orden de compra no encontrada")
    return PurchaseOrderResponse.model_validate(row)


@router.get(
    "/{id_orden_compra}/details",
    response_model=list[PurchaseOrderDetailResponse],
)
def read_purchase_order_details(
    id_orden_compra: Annotated[int, Path(gt=0)],
    db: Session = Depends(get_compras_db),
) -> list[PurchaseOrderDetailResponse]:
    if get_purchase_order(db, id_orden_compra) is None:
        raise HTTPException(status_code=404, detail="Orden de compra no encontrada")
    rows = list_purchase_order_details(db, id_orden_compra)
    return [PurchaseOrderDetailResponse.model_validate(row) for row in rows]


@router.post("/{id_orden_compra}/cancel", response_model=PurchaseOrderResponse)
def cancel_order(
    id_orden_compra: Annotated[int, Path(gt=0)],
    db: Session = Depends(get_compras_db),
) -> PurchaseOrderResponse:
    try:
        set_local_transaction_timeouts(db)
        row = cancel_purchase_order(db, id_orden_compra)
        if row is None:
            existing = get_purchase_order(db, id_orden_compra)
            db.rollback()
            if existing is None:
                raise HTTPException(status_code=404, detail="Orden de compra no encontrada")
            raise HTTPException(
                status_code=409,
                detail="Solo se pueden cancelar órdenes pendientes",
            )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="No fue posible cancelar la orden") from None
    return PurchaseOrderResponse.model_validate(row)
