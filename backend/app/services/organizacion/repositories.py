from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def site_exists(db: Session, id_sede: int) -> bool:
    return (
        db.execute(
            text("""
                SELECT 1
                FROM organizacion.sedes
                WHERE id_sede = :id_sede
            """),
            {"id_sede": id_sede},
        ).first()
        is not None
    )


def list_sites(
    db: Session,
    *,
    estado: str | None,
    tipo_sede: str | None,
    search: str | None = None,
    limit: int,
    offset: int,
) -> list[dict[str, Any]]:
    conditions: list[str] = []
    parameters: dict[str, Any] = {"limit": limit, "offset": offset}
    if estado is not None:
        conditions.append("estado = :estado")
        parameters["estado"] = estado
    if tipo_sede is not None:
        conditions.append("tipo_sede = :tipo_sede")
        parameters["tipo_sede"] = tipo_sede
    if search is not None:
        conditions.append("(nombre ILIKE :search OR ciudad ILIKE :search)")
        parameters["search"] = f"%{search}%"

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    result = db.execute(
        text(f"""
            SELECT id_sede, nombre, ciudad, direccion, tipo_sede, estado
            FROM organizacion.sedes
            {where_clause}
            ORDER BY id_sede
            LIMIT :limit OFFSET :offset
        """),
        parameters,
    )
    return [dict(row) for row in result.mappings().all()]


def get_site(db: Session, id_sede: int) -> dict[str, Any] | None:
    row = db.execute(
        text("""
            SELECT id_sede, nombre, ciudad, direccion, tipo_sede, estado
            FROM organizacion.sedes
            WHERE id_sede = :id_sede
        """),
        {"id_sede": id_sede},
    ).mappings().first()
    return dict(row) if row is not None else None


def create_site(db: Session, values: dict[str, Any]) -> dict[str, Any]:
    row = db.execute(
        text("""
            INSERT INTO organizacion.sedes
                (nombre, ciudad, direccion, tipo_sede, estado)
            VALUES
                (:nombre, :ciudad, :direccion, :tipo_sede, :estado)
            RETURNING id_sede, nombre, ciudad, direccion, tipo_sede, estado
        """),
        values,
    ).mappings().one()
    return dict(row)


def update_site(
    db: Session,
    id_sede: int,
    values: dict[str, Any],
) -> dict[str, Any] | None:
    allowed = {"nombre", "ciudad", "direccion", "tipo_sede", "estado"}
    if not values:
        return get_site(db, id_sede)
    if not values.keys() <= allowed:
        raise ValueError("Invalid site fields")
    assignments = ", ".join(f"{key} = :{key}" for key in values)
    row = db.execute(
        text(f"""
            UPDATE organizacion.sedes
            SET {assignments}
            WHERE id_sede = :id_sede
            RETURNING id_sede, nombre, ciudad, direccion, tipo_sede, estado
        """),
        {**values, "id_sede": id_sede},
    ).mappings().first()
    return dict(row) if row is not None else None


def list_warehouses(
    db: Session,
    *,
    estado: str | None,
    tipo_almacen: str | None,
    id_sede: int | None,
    search: str | None = None,
    limit: int,
    offset: int,
) -> list[dict[str, Any]]:
    conditions: list[str] = []
    parameters: dict[str, Any] = {"limit": limit, "offset": offset}
    if estado is not None:
        conditions.append("estado = :estado")
        parameters["estado"] = estado
    if tipo_almacen is not None:
        conditions.append("tipo_almacen = :tipo_almacen")
        parameters["tipo_almacen"] = tipo_almacen
    if id_sede is not None:
        conditions.append("id_sede = :id_sede")
        parameters["id_sede"] = id_sede
    if search is not None:
        conditions.append("nombre ILIKE :search")
        parameters["search"] = f"%{search}%"

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    result = db.execute(
        text(f"""
            SELECT id_almacen, id_sede, nombre, tipo_almacen, estado
            FROM organizacion.almacenes
            {where_clause}
            ORDER BY id_almacen
            LIMIT :limit OFFSET :offset
        """),
        parameters,
    )
    return [dict(row) for row in result.mappings().all()]


def get_warehouse(db: Session, id_almacen: int) -> dict[str, Any] | None:
    row = db.execute(
        text("""
            SELECT id_almacen, id_sede, nombre, tipo_almacen, estado
            FROM organizacion.almacenes
            WHERE id_almacen = :id_almacen
        """),
        {"id_almacen": id_almacen},
    ).mappings().first()
    return dict(row) if row is not None else None


def create_warehouse(db: Session, values: dict[str, Any]) -> dict[str, Any]:
    row = db.execute(
        text("""
            INSERT INTO organizacion.almacenes
                (id_sede, nombre, tipo_almacen, estado)
            VALUES
                (:id_sede, :nombre, :tipo_almacen, :estado)
            RETURNING id_almacen, id_sede, nombre, tipo_almacen, estado
        """),
        values,
    ).mappings().one()
    return dict(row)


def update_warehouse(
    db: Session,
    id_almacen: int,
    values: dict[str, Any],
) -> dict[str, Any] | None:
    allowed = {"id_sede", "nombre", "tipo_almacen", "estado"}
    if not values:
        return get_warehouse(db, id_almacen)
    if not values.keys() <= allowed:
        raise ValueError("Invalid warehouse fields")
    assignments = ", ".join(f"{key} = :{key}" for key in values)
    row = db.execute(
        text(f"""
            UPDATE organizacion.almacenes
            SET {assignments}
            WHERE id_almacen = :id_almacen
            RETURNING id_almacen, id_sede, nombre, tipo_almacen, estado
        """),
        {**values, "id_almacen": id_almacen},
    ).mappings().first()
    return dict(row) if row is not None else None
