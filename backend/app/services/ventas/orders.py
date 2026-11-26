from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.services.ventas.dependencies import get_ventas_db
from app.services.ventas.repositories import (
    create_order,
    get_customer,
    get_order,
    list_order_details,
    list_orders,
)
from app.services.ventas.schemas import (
    OrderCreate,
    OrderDetailResponse,
    OrderResponse,
    OrderState,
)
from app.shared.clients import request_service
from app.shared.exceptions import RemoteServiceError
from app.shared.transactions import set_local_transaction_timeouts
from app.shared.audit import set_audit_details

router = APIRouter(prefix="/orders", tags=["Pedidos"])


def _validate_remote_resource(
    request: Request,
    *,
    service: str,
    path: str,
    id_field: str,
    expected_id: int,
) -> dict:
    scheme, _, bearer_token = request.headers.get("authorization", "").partition(" ")
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
    if (
        not isinstance(resource, dict)
        or resource.get(id_field) != expected_id
        or resource.get("estado") != "activo"
    ):
        raise HTTPException(status_code=422, detail=f"La referencia no está activa en {service}")
    return resource


def _bearer_token(request: Request) -> str:
    scheme, _, bearer_token = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not bearer_token:
        raise HTTPException(status_code=401, detail="Credenciales no válidas")
    return bearer_token


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def add_order(
    data: OrderCreate,
    request: Request,
    db: Session = Depends(get_ventas_db),
) -> OrderResponse:
    site = _validate_remote_resource(
        request,
        service="organizacion",
        path=f"/sedes/{data.id_sede}",
        id_field="id_sede",
        expected_id=data.id_sede,
    )
    warehouse = _validate_remote_resource(
        request,
        service="organizacion",
        path=f"/warehouses/{data.id_almacen}",
        id_field="id_almacen",
        expected_id=data.id_almacen,
    )
    if warehouse.get("id_sede") != site["id_sede"]:
        raise HTTPException(status_code=422, detail="El almacén no pertenece a la sede indicada")
    employee = _validate_remote_resource(
        request,
        service="identidad",
        path=f"/employees/{data.id_empleado}",
        id_field="id_empleado",
        expected_id=data.id_empleado,
    )
    if employee.get("id_sede") != data.id_sede:
        raise HTTPException(status_code=422, detail="El empleado no pertenece a la sede indicada")

    set_local_transaction_timeouts(db)
    customer = get_customer(db, data.id_cliente)
    if customer is None:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    if customer["estado"] != "activo":
        raise HTTPException(status_code=409, detail="El cliente está inactivo")

    products = []
    for item in data.productos:
        product = _validate_remote_resource(
            request,
            service="catalogo",
            path=f"/products/{item.id_producto}",
            id_field="id_producto",
            expected_id=item.id_producto,
        )
        try:
            stock = request_service(
                "inventarios",
                "GET",
                "/stock",
                bearer_token=_bearer_token(request),
                params={
                    "id_almacen": data.id_almacen,
                    "id_producto": item.id_producto,
                    "limit": 1,
                },
            )
        except RemoteServiceError as error:
            raise HTTPException(
                status_code=503 if error.status_code == 503 else 502,
                detail="No fue posible consultar las existencias en Inventarios",
            ) from None
        if not isinstance(stock, list) or any(
            not isinstance(row, dict) for row in stock
        ):
            raise HTTPException(
                status_code=502,
                detail="Inventarios devolvió una respuesta inválida",
            )
        inventory = next(
            (
                row
                for row in stock
                if row.get("id_almacen") == data.id_almacen
                and row.get("id_producto") == item.id_producto
            ),
            None,
        )
        if inventory is None or not isinstance(
            inventory.get("existencia_actual"), int
        ):
            raise HTTPException(
                status_code=502,
                detail="Inventarios no devolvió la existencia solicitada",
            )
        if inventory["existencia_actual"] < item.cantidad:
            raise HTTPException(
                status_code=409,
                detail=f"Existencias insuficientes para el producto {item.id_producto}",
            )
        products.append(
            {
                "id_producto": item.id_producto,
                "cantidad": item.cantidad,
                "precio_unitario": product["precio_lista"],
            }
        )

    try:
        row = create_order(
            db,
            id_sede=data.id_sede,
            id_almacen=data.id_almacen,
            id_cliente=data.id_cliente,
            id_empleado=data.id_empleado,
            products=products,
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="No fue posible crear el pedido") from None
    set_audit_details(
        request,
        object_type="ventas.pedidos",
        object_id=row["id_pedido"],
        after=row,
        details={"productos": products},
    )
    return OrderResponse.model_validate(row)


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
