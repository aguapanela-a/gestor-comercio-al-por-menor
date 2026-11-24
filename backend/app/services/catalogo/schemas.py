from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


CatalogState = Literal["activo", "inactivo"]


class CatalogInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CategoryResponse(BaseModel):
    id_categoria: int
    nombre: str = Field(max_length=80)
    descripcion: str | None = Field(default=None, max_length=200)
    estado: CatalogState


class ProductResponse(BaseModel):
    id_producto: int
    sku: str = Field(max_length=30)
    nombre: str = Field(max_length=120)
    id_categoria: int
    unidad_medida: str = Field(max_length=20)
    precio_lista: Decimal = Field(ge=0)
    estado: CatalogState


class CategoryCreate(CatalogInput):
    nombre: str = Field(min_length=1, max_length=80)
    descripcion: str | None = Field(default=None, max_length=200)
    estado: CatalogState = "activo"


class CategoryUpdate(CatalogInput):
    nombre: str | None = Field(default=None, min_length=1, max_length=80)
    descripcion: str | None = Field(default=None, max_length=200)
    estado: CatalogState | None = None


class ProductCreate(CatalogInput):
    sku: str = Field(min_length=1, max_length=30)
    nombre: str = Field(min_length=1, max_length=120)
    id_categoria: int = Field(gt=0)
    unidad_medida: str = Field(min_length=1, max_length=20)
    precio_lista: Decimal = Field(ge=0)
    estado: CatalogState = "activo"


class ProductUpdate(CatalogInput):
    sku: str | None = Field(default=None, min_length=1, max_length=30)
    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    id_categoria: int | None = Field(default=None, gt=0)
    unidad_medida: str | None = Field(default=None, min_length=1, max_length=20)
    precio_lista: Decimal | None = Field(default=None, ge=0)
    estado: CatalogState | None = None
