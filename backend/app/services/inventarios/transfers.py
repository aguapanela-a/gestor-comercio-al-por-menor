from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.services.inventarios.dependencies import get_inventarios_db
from app.services.inventarios.repositories import (
    get_transfer,
    list_transfer_details,
    list_transfers,
)
from app.services.inventarios.schemas import (
    TransferDetailResponse,
    TransferResponse,
    TransferState,
)

router = APIRouter(
    prefix="/transfers",
    tags=["Transferencias"],
    dependencies=[Depends(get_current_user)],
)


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
