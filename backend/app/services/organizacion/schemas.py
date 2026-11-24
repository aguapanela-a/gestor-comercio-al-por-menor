from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


SiteState = Literal["activo", "inactivo"]
SiteType = Literal["comercial", "distribucion"]
WarehouseType = Literal["principal", "venta", "recepcion"]


class SiteResponse(BaseModel):
    id_sede: int
    nombre: str = Field(max_length=80)
    ciudad: str = Field(max_length=60)
    direccion: str = Field(max_length=120)
    tipo_sede: SiteType
    estado: SiteState


class WarehouseResponse(BaseModel):
    id_almacen: int
    id_sede: int
    nombre: str = Field(max_length=80)
    tipo_almacen: WarehouseType
    estado: SiteState


class OrganizationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SiteCreate(OrganizationInput):
    nombre: str = Field(min_length=1, max_length=80)
    ciudad: str = Field(min_length=1, max_length=60)
    direccion: str = Field(min_length=1, max_length=120)
    tipo_sede: SiteType
    estado: SiteState = "activo"


class SiteUpdate(OrganizationInput):
    nombre: str | None = Field(default=None, min_length=1, max_length=80)
    ciudad: str | None = Field(default=None, min_length=1, max_length=60)
    direccion: str | None = Field(default=None, min_length=1, max_length=120)
    tipo_sede: SiteType | None = None
    estado: SiteState | None = None


class WarehouseCreate(OrganizationInput):
    id_sede: int = Field(gt=0)
    nombre: str = Field(min_length=1, max_length=80)
    tipo_almacen: WarehouseType
    estado: SiteState = "activo"


class WarehouseUpdate(OrganizationInput):
    id_sede: int | None = Field(default=None, gt=0)
    nombre: str | None = Field(default=None, min_length=1, max_length=80)
    tipo_almacen: WarehouseType | None = None
    estado: SiteState | None = None
