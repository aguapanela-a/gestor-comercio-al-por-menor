from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


PurchaseState = Literal[
    "pendiente",
    "recibida_parcial",
    "completada",
    "cancelada",
]
ReceiptState = Literal["procesada", "anulada"]
ResourceState = Literal["activo", "inactivo"]


class PurchaseInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SupplierCreate(PurchaseInput):
    identificacion: str | None = Field(default=None, max_length=20)
    razon_social: str | None = Field(default=None, max_length=100)
    ciudad: str | None = Field(default=None, max_length=50)
    correo: str | None = Field(default=None, max_length=100)
    telefono: str | None = Field(default=None, max_length=20)
    estado: ResourceState = "activo"


class SupplierUpdate(PurchaseInput):
    identificacion: str | None = Field(default=None, max_length=20)
    razon_social: str | None = Field(default=None, max_length=100)
    ciudad: str | None = Field(default=None, max_length=50)
    correo: str | None = Field(default=None, max_length=100)
    telefono: str | None = Field(default=None, max_length=20)
    estado: ResourceState | None = None


class SupplierResponse(BaseModel):
    id_proveedor: int
    identificacion: str | None
    razon_social: str | None
    ciudad: str | None
    correo: str | None
    telefono: str | None
    estado: ResourceState


class ProductSupplierInput(PurchaseInput):
    costo_referencia: Decimal = Field(ge=0)
    plazo_entrega_dias: int = Field(ge=0)
    estado: ResourceState = "activo"


class ProductSupplierResponse(BaseModel):
    id_producto: int
    id_proveedor: int
    costo_referencia: Decimal = Field(ge=0)
    plazo_entrega_dias: int = Field(ge=0)
    estado: ResourceState


class PurchaseOrderResponse(BaseModel):
    id_orden_compra: int
    id_proveedor: int
    id_almacen_destino: int
    id_empleado_creador: int
    fecha_orden: datetime
    fecha_estimada: date | None
    estado: PurchaseState


class PurchaseOrderItemInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id_producto: int = Field(gt=0)
    cantidad_solicitada: int = Field(gt=0)


class PurchaseOrderCreate(PurchaseInput):
    id_proveedor: int = Field(gt=0)
    id_almacen_destino: int = Field(gt=0)
    id_empleado_creador: int = Field(gt=0)
    fecha_estimada: date
    productos: list[PurchaseOrderItemInput] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_products(self) -> "PurchaseOrderCreate":
        ids = [item.id_producto for item in self.productos]
        if len(ids) != len(set(ids)):
            raise ValueError("Cada producto debe aparecer una sola vez")
        return self


class PurchaseReceiptItemInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id_producto: int = Field(gt=0)
    cantidad_total_recibida: int = Field(gt=0)


class PurchaseReceiptCreate(PurchaseInput):
    productos: list[PurchaseReceiptItemInput] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_products(self) -> "PurchaseReceiptCreate":
        ids = [item.id_producto for item in self.productos]
        if len(ids) != len(set(ids)):
            raise ValueError("Cada producto debe aparecer una sola vez")
        return self


class PurchaseReceiptRegistrationResponse(BaseModel):
    id_recepcion: int | None
    id_orden_compra: int
    fecha_recepcion: datetime | None
    estado: ReceiptState
    cantidades_actualizadas: bool


class ReceiptResponse(BaseModel):
    id_recepcion: int
    id_orden_compra: int
    fecha_recepcion: datetime
    estado: ReceiptState


class PurchaseOrderDetailResponse(BaseModel):
    id_orden_compra: int
    id_producto: int
    cantidad_solicitada: int
    costo_unitario: Decimal = Field(ge=0)
    cantidad_recibida: int
    cantidad_pendiente: int


class ReceiptDetailResponse(BaseModel):
    id_recepcion: int
    id_producto: int
    cantidad_recibida: int
