from collections.abc import Sequence
from typing import Any

from app.services.reportes.aplicacion.puertos_salida import OutPortViews
from app.services.reportes.aplicacion.registryStrategy.view_out import ViewOut


class DynamicViewDispatcher(OutPortViews):
    def __init__(self, views: Sequence[ViewOut]) -> None:
        self._views: dict[str, ViewOut] = {}
        for view in views:
            entity_name = view.getEntityName()
            if entity_name in self._views:
                raise ValueError(f"Vista duplicada en el registro: {entity_name}")
            self._views[entity_name] = view

    def getView(self, entityName: str) -> list[dict[str, Any]]:
        try:
            view = self._views[entityName]
        except KeyError as error:
            raise ValueError(f"Vista no registrada: {entityName}") from error
        return view.getViewOut()
