from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.services.inventarios.dependencies import get_inventarios_db
from app.services.inventarios.repositories import (
    cancel_transfer,
    create_transfer,
    dispatch_transfer,
    get_transfer,
    list_transfer_details,
    list_transfers,
    receive_transfer,
)
from app.services.inventarios.schemas import (
    TransferCreate,
    TransferDetailResponse,
    TransferReceiptCreate,
    TransferResponse,
    TransferState,
)
from app.shared.clients import request_service
from app.shared.exceptions import RemoteServiceError
from app.shared.transactions import set_local_transaction_timeouts
from app.shared.audit import set_audit_details

router = APIRouter(
    prefix="/transfers",
    tags=["Transferencias"],
    dependencies=[Depends(get_current_user)],
)


def _validate_remote_resource(
    request: Request,
    service: str,
    path: str,
    expected_id: int,
    id_field: str,
    *,
    require_active: bool = True,
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
    if not isinstance(resource, dict) or resource.get(id_field) != expected_id:
        raise HTTPException(status_code=502, detail=f"Respuesta inválida de {service}")
    if require_active and resource.get("estado") != "activo":
        raise HTTPException(status_code=422, detail=f"La referencia no está activa en {service}")
    return resource


@router.post("", response_model=TransferResponse, status_code=status.HTTP_201_CREATED)
def add_transfer(
    data: TransferCreate,
    request: Request,
    db: Session = Depends(get_inventarios_db),
) -> TransferResponse:
    _validate_remote_resource(
        request, "organizacion", f"/warehouses/{data.id_almacen_origen}",
        data.id_almacen_origen, "id_almacen",
    )
    _validate_remote_resource(
        request, "organizacion", f"/warehouses/{data.id_almacen_destino}",
        data.id_almacen_destino, "id_almacen",
    )
    for item in data.productos:
        _validate_remote_resource(
            request, "catalogo", f"/products/{item.id_producto}",
            item.id_producto, "id_producto",
        )
    try:
        set_local_transaction_timeouts(db)
        row = create_transfer(
            db,
            id_almacen_origen=data.id_almacen_origen,
            id_almacen_destino=data.id_almacen_destino,
            products=[
                {
                    "id_producto": item.id_producto,
                    "cantidad_enviada": item.cantidad_enviada,
                }
                for item in data.productos
            ],
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="No fue posible crear la transferencia") from None
    set_audit_details(
        request,
        object_type="inventarios.transferencias",
        object_id=row["id_transferencia"],
        after=row,
        details={"productos": [item.model_dump(mode="json") for item in data.productos]},
    )
    return TransferResponse.model_validate(row)


@router.get("", response_model=list[TransferResponse])
def read_transfers(
    estado: Annotated[TransferState | None, Query()] = None,
    id_almacen: Annotated[int | None, Query(gt=0)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=100_000)] = 0,
    db: Session = Depends(get_inventarios_db),
) -> list[TransferResponse]:
    rows = list_transfers(
        db,
        estado=estado,
        id_almacen=id_almacen,
        limit=limit,
        offset=offset,
    )
    return [TransferResponse.model_validate(row) for row in rows]


@router.get("/{id_transferencia}", response_model=TransferResponse)
def read_transfer(
    id_transferencia: Annotated[int, Path(gt=0)],
    db: Session = Depends(get_inventarios_db),
) -> TransferResponse:
    row = get_transfer(db, id_transferencia)
    if row is None:
        raise HTTPException(status_code=404, detail="Transferencia no encontrada")
    return TransferResponse.model_validate(row)


@router.get(
    "/{id_transferencia}/details",
    response_model=list[TransferDetailResponse],
)
def read_transfer_details(
    id_transferencia: Annotated[int, Path(gt=0)],
    db: Session = Depends(get_inventarios_db),
) -> list[TransferDetailResponse]:
    if get_transfer(db, id_transferencia) is None:
        raise HTTPException(status_code=404, detail="Transferencia no encontrada")
    rows = list_transfer_details(db, id_transferencia)
    return [TransferDetailResponse.model_validate(row) for row in rows]


@router.post("/{id_transferencia}/dispatch", response_model=TransferResponse)
def dispatch(
    id_transferencia: Annotated[int, Path(gt=0)],
    request: Request,
    db: Session = Depends(get_inventarios_db),
) -> TransferResponse:
    before = get_transfer(db, id_transferencia)
    try:
        set_local_transaction_timeouts(db)
        row = dispatch_transfer(db, id_transferencia)
        if row is None:
            db.rollback()
            raise HTTPException(status_code=404, detail="Transferencia no encontrada")
        db.commit()
    except ValueError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(error)) from None
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="No fue posible despachar la transferencia") from None
    set_audit_details(
        request,
        object_type="inventarios.transferencias",
        object_id=id_transferencia,
        before=before,
        after=row,
        details={"operacion": "despacho"},
    )
    return TransferResponse.model_validate(row)


@router.put("/{id_transferencia}/receipts", response_model=TransferResponse)
def receive(
    id_transferencia: Annotated[int, Path(gt=0)],
    data: TransferReceiptCreate,
    request: Request,
    db: Session = Depends(get_inventarios_db),
) -> TransferResponse:
    set_local_transaction_timeouts(db)
    transfer = get_transfer(db, id_transferencia)
    if transfer is None:
        raise HTTPException(status_code=404, detail="Transferencia no encontrada")
    before_details = list_transfer_details(db, id_transferencia)
    warehouse = _validate_remote_resource(
        request,
        "organizacion",
        f"/warehouses/{transfer['id_almacen_destino']}",
        transfer["id_almacen_destino"],
        "id_almacen",
        require_active=False,
    )
    try:
        row = receive_transfer(
            db,
            id_transferencia=id_transferencia,
            id_sede_destino=warehouse["id_sede"],
            received_totals={
                item.id_producto: item.cantidad_total_recibida
                for item in data.productos
            },
        )
        if row is None:
            db.rollback()
            raise HTTPException(status_code=404, detail="Transferencia no encontrada")
        db.commit()
    except ValueError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(error)) from None
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="No fue posible registrar la recepción") from None
    set_audit_details(
        request,
        object_type="inventarios.transferencias",
        object_id=id_transferencia,
        before={"transferencia": transfer, "detalles": before_details},
        after=row,
        details={
            "operacion": "recepcion",
            "productos_recibidos": [
                {
                    "id_producto": item.id_producto,
                    "cantidad_total_recibida": item.cantidad_total_recibida,
                }
                for item in data.productos
            ],
        },
    )
    return TransferResponse.model_validate(row)


@router.post("/{id_transferencia}/cancel", response_model=TransferResponse)
def cancel(
    id_transferencia: Annotated[int, Path(gt=0)],
    request: Request,
    db: Session = Depends(get_inventarios_db),
) -> TransferResponse:
    set_local_transaction_timeouts(db)
    before = get_transfer(db, id_transferencia)
    row = cancel_transfer(db, id_transferencia)
    if row is None:
        existing = get_transfer(db, id_transferencia)
        db.rollback()
        if existing is None:
            raise HTTPException(status_code=404, detail="Transferencia no encontrada")
        raise HTTPException(
            status_code=409,
            detail="Solo se pueden cancelar transferencias solicitadas",
        )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="No fue posible cancelar la transferencia") from None
    set_audit_details(
        request,
        object_type="inventarios.transferencias",
        object_id=id_transferencia,
        before=before,
        after=row,
        details={"operacion": "cancelacion"},
    )
    return TransferResponse.model_validate(row)
