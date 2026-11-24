from typing import Any

from psycopg import Connection

from app.services.reportes.aplicacion.registryStrategy import ViewOut


class BaseViewAdapter(ViewOut):
    entity_name: str
    query: str | None = None

    def __init__(self, connection: Connection[Any]) -> None:
        self.connection = connection

    def getViewOut(self) -> list[dict[str, Any]]:
        if self.query is None:
            raise NotImplementedError(
                f"La consulta para {self.getEntityName()} aún no está definida."
            )

        with self.connection.cursor() as cursor:
            cursor.execute(self.query)
            results = cursor.fetchall()
            if cursor.description is None:
                raise RuntimeError(
                    f"La consulta para {self.getEntityName()} no devolvió columnas."
                )
            columns = [description.name for description in cursor.description]
            return [dict(zip(columns, row, strict=True)) for row in results]

    def getEntityName(self) -> str:
        return self.entity_name
