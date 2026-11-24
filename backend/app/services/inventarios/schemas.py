from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


TransferState = Literal["solicitada", "despachada", "completada", "cancelada"]


class InventoryResponse(BaseModel):
    id_almacen: int | None
    id_producto: int
    id_sede: int
    existencia_actual: int
    stock_minimo: int
    fecha_actualizacion: datetime


class StockMinimumUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id_almacen: int = Field(gt=0)
    id_producto: int = Field(gt=0)
    stock_minimo: int = Field(ge=0)


class TransferResponse(BaseModel):
    id_transferencia: int
    id_almacen_origen: int
    id_almacen_destino: int
    fecha_solicitud: datetime
    fecha_despacho: datetime | None
    fecha_recepcion: datetime | None
    estado: TransferState


class TransferDetailResponse(BaseModel):
    id_transferencia: int
    id_producto: int
    cantidad_enviada: int
    cantidad_recibida: int | None
