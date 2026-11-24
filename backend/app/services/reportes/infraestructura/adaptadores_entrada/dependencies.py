from typing import Any

from fastapi import Depends
from psycopg import Connection

from app.services.reportes.aplicacion.puertos_entrada import InPortViews
from app.services.reportes.aplicacion.registryStrategy import DynamicViewDispatcher
from app.services.reportes.aplicacion.useCases import UseCaseViews
from app.services.reportes.infraestructura.adaptadores_salida import (
    View1 as View1Adapter,
    View2 as View2Adapter,
    View3 as View3Adapter,
    View4 as View4Adapter,
    View5 as View5Adapter,
    View6 as View6Adapter,
    View7 as View7Adapter,
    View8 as View8Adapter,
    View9 as View9Adapter,
    View10 as View10Adapter,
)
from app.services.reportes.infraestructura.configuracion import get_connection


def get_use_case_views(
    connection: Connection[Any] = Depends(get_connection),
) -> InPortViews:
    views = [
        View1Adapter(connection),
        View2Adapter(connection),
        View3Adapter(connection),
        View4Adapter(connection),
        View5Adapter(connection),
        View6Adapter(connection),
        View7Adapter(connection),
        View8Adapter(connection),
        View9Adapter(connection),
        View10Adapter(connection),
    ]
    return UseCaseViews(DynamicViewDispatcher(views))
