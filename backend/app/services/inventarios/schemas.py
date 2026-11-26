from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


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


class StockAdjustment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id_almacen: int = Field(gt=0)
    id_producto: int = Field(gt=0)
    existencia_objetivo: int = Field(ge=0)


class TransferItemInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id_producto: int = Field(gt=0)
    cantidad_enviada: int = Field(gt=0)


class TransferCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id_almacen_origen: int = Field(gt=0)
    id_almacen_destino: int = Field(gt=0)
    productos: list[TransferItemInput] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_transfer(self) -> "TransferCreate":
        if self.id_almacen_origen == self.id_almacen_destino:
            raise ValueError("Los almacenes deben ser diferentes")
        ids = [item.id_producto for item in self.productos]
        if len(ids) != len(set(ids)):
            raise ValueError("Cada producto debe aparecer una sola vez")
        return self


class TransferReceiptItemInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id_producto: int = Field(gt=0)
    cantidad_total_recibida: int = Field(ge=0)


class TransferReceiptCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    productos: list[TransferReceiptItemInput] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_products(self) -> "TransferReceiptCreate":
        ids = [item.id_producto for item in self.productos]
        if len(ids) != len(set(ids)):
            raise ValueError("Cada producto debe aparecer una sola vez")
        return self


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



class SalesDispatchItemInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id_producto: int = Field(gt=0)
    cantidad: int = Field(gt=0)


class SalesDispatchCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id_pedido: int = Field(gt=0)
    id_sede: int = Field(gt=0)
    id_almacen: int = Field(gt=0)
    productos: list[SalesDispatchItemInput] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_products(self) -> "SalesDispatchCreate":
        ids = [item.id_producto for item in self.productos]
        if len(ids) != len(set(ids)):
            raise ValueError("Cada producto debe aparecer una sola vez")
        return self


class SalesReturnCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id_devolucion: int = Field(gt=0)
    id_pedido: int = Field(gt=0)
    id_sede: int = Field(gt=0)
    id_almacen: int = Field(gt=0)
    productos: list[SalesDispatchItemInput]

    @model_validator(mode="after")
    def validate_products(self) -> "SalesReturnCreate":
        ids = [item.id_producto for item in self.productos]
        if len(ids) != len(set(ids)):
            raise ValueError("Cada producto debe aparecer una sola vez")
        return self
