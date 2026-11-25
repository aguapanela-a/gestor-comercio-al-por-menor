import re
from collections.abc import Mapping
from typing import Any

from psycopg import Connection, sql
from psycopg.errors import InsufficientPrivilege, UndefinedTable

REPORTS_SCHEMA = "reportes"

_VIEW_CATALOG_QUERY = """
    SELECT
        c.relname AS name,
        n.nspname AS schema_name,
        obj_description(c.oid, 'pg_class') AS description,
        COALESCE(
            json_agg(
                json_build_object(
                    'name', a.attname,
                    'type', format_type(a.atttypid, a.atttypmod),
                    'nullable', NOT a.attnotnull,
                    'description', col_description(c.oid, a.attnum)
                )
                ORDER BY a.attnum
            ) FILTER (WHERE a.attnum IS NOT NULL),
            '[]'::json
        ) AS columns
    FROM pg_class AS c
    JOIN pg_namespace AS n ON n.oid = c.relnamespace
    LEFT JOIN pg_attribute AS a
        ON a.attrelid = c.oid
        AND a.attnum > 0
        AND NOT a.attisdropped
    WHERE n.nspname = %s
      AND c.relkind = 'v'
      AND has_schema_privilege(current_user, n.oid, 'USAGE')
      AND has_table_privilege(current_user, c.oid, 'SELECT')
      AND left(c.relname, 1) <> '_'
      AND left(c.relname, 3) <> 'pg_'
    GROUP BY c.oid, n.nspname, c.relname
    ORDER BY c.relname
"""

_VIEW_LOOKUP_QUERY = """
    SELECT c.relname AS name
    FROM pg_class AS c
    JOIN pg_namespace AS n ON n.oid = c.relnamespace
    WHERE n.nspname = %s
      AND c.relname = %s
      AND c.relkind = 'v'
      AND has_schema_privilege(current_user, n.oid, 'USAGE')
      AND has_table_privilege(current_user, c.oid, 'SELECT')
      AND left(c.relname, 1) <> '_'
      AND left(c.relname, 3) <> 'pg_'
"""


class ReportViewNotFound(LookupError):
    pass


class ReportViewCatalog:
    def __init__(self, connection: Connection[Any]) -> None:
        self._connection = connection

    def list_views(self) -> list[dict[str, Any]]:
        with self._connection.cursor() as cursor:
            cursor.execute(_VIEW_CATALOG_QUERY, (REPORTS_SCHEMA,))
            views = cursor.fetchall()

        return [
            {
                "name": view["name"],
                "schema": view["schema_name"],
                "description": view["description"],
                "columns": view["columns"],
                "label": _label_for_view(view["name"]),
            }
            for view in views
        ]

    def get_view_rows(self, view_name: str) -> list[dict[str, Any]]:
        with self._connection.cursor() as cursor:
            cursor.execute(_VIEW_LOOKUP_QUERY, (REPORTS_SCHEMA, view_name))
            if cursor.fetchone() is None:
                raise ReportViewNotFound(view_name)

            query = sql.SQL("SELECT * FROM {}.{}").format(
                sql.Identifier(REPORTS_SCHEMA),
                sql.Identifier(view_name),
            )
            try:
                cursor.execute(query)
            except (InsufficientPrivilege, UndefinedTable) as error:
                raise ReportViewNotFound(view_name) from error

            rows = cursor.fetchall()
            if cursor.description is None:
                return []
            columns = [description.name for description in cursor.description]

        return [
            dict(row)
            if isinstance(row, Mapping)
            else dict(zip(columns, row, strict=True))
            for row in rows
        ]


def _label_for_view(name: str) -> str:
    readable_name = re.sub(r"_+", " ", name.removeprefix("vista_")).strip()
    return readable_name.capitalize()
