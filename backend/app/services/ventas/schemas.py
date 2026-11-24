from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


SalesState = Literal["activo", "inactivo"]
OrderState = Literal["pendiente", "completado", "cancelado", "devolucion"]
PaymentState = Literal["aprobado", "rechazado", "anulado"]
PaymentMethod = Literal[
    "efectivo",
    "tarjeta_credito",
    "tarjeta_debito",
    "transferencia",
]
ReturnState = Literal["pendiente", "aprobada", "rechazada"]
ProductCondition = Literal["buen_estado", "defectuoso", "empaque_abierto"]


class SalesInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CustomerCreate(SalesInput):
    tipo_documento: str | None = Field(default=None, max_length=5)
    num_documento: str | None = Field(default=None, max_length=20)
    nombre_completo: str | None = Field(default=None, max_length=120)
    correo: str | None = Field(default=None, max_length=100)
    telefono: str | None = Field(default=None, max_length=20)
    estado: SalesState = "activo"


class CustomerUpdate(SalesInput):
    tipo_documento: str | None = Field(default=None, max_length=5)
    num_documento: str | None = Field(default=None, max_length=20)
    nombre_completo: str | None = Field(default=None, max_length=120)
    correo: str | None = Field(default=None, max_length=100)
    telefono: str | None = Field(default=None, max_length=20)
    estado: SalesState | None = None


class CustomerResponse(BaseModel):
    id_cliente: int
    tipo_documento: str | None
    num_documento: str | None
    nombre_completo: str | None
    correo: str | None
    telefono: str | None
    estado: SalesState


class OrderResponse(BaseModel):
    id_pedido: int
    id_sede: int
    id_almacen: int
    id_cliente: int
    id_empleado: int
    fecha_pedido: datetime
    estado: OrderState
    total_registrado: Decimal


class OrderDetailResponse(BaseModel):
    id_pedido: int
    id_producto: int
    cantidad: int
    precio_unitario: Decimal


class PaymentResponse(BaseModel):
    id_pago: int
    id_pedido: int
    fecha_pago: date
    valor: Decimal
    medio_pago: PaymentMethod
    estado: PaymentState


class ReturnResponse(BaseModel):
    id_devolucion: int
    id_pedido: int
    fecha_solicitud: date
    motivo: str | None
    estado: ReturnState


class ReturnDetailResponse(BaseModel):
    id_devolucion: int
    id_producto: int
    cantidad: int
    condicion_producto: ProductCondition
