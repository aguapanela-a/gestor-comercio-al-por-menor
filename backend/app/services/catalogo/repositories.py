from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def category_exists(db: Session, id_categoria: int) -> bool:
    return (
        db.execute(
            text("""
                SELECT 1
                FROM catalogo.categorias
                WHERE id_categoria = :id_categoria
            """),
            {"id_categoria": id_categoria},
        ).first()
        is not None
    )


def list_categories(
    db: Session,
    *,
    estado: str | None,
    search: str | None = None,
    limit: int,
    offset: int,
) -> list[dict[str, Any]]:
    conditions: list[str] = []
    parameters: dict[str, Any] = {"limit": limit, "offset": offset}
    if estado is not None:
        conditions.append("estado = :estado")
        parameters["estado"] = estado
    if search is not None:
        conditions.append("nombre ILIKE :search")
        parameters["search"] = f"%{search}%"

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    result = db.execute(
        text(f"""
            SELECT id_categoria, nombre, descripcion, estado
            FROM catalogo.categorias
            {where_clause}
            ORDER BY id_categoria
            LIMIT :limit OFFSET :offset
        """),
        parameters,
    )
    return [dict(row) for row in result.mappings().all()]


def get_category(db: Session, id_categoria: int) -> dict[str, Any] | None:
    row = db.execute(
        text("""
            SELECT id_categoria, nombre, descripcion, estado
            FROM catalogo.categorias
            WHERE id_categoria = :id_categoria
        """),
        {"id_categoria": id_categoria},
    ).mappings().first()
    return dict(row) if row is not None else None


def create_category(db: Session, values: dict[str, Any]) -> dict[str, Any]:
    row = db.execute(
        text("""
            INSERT INTO catalogo.categorias (nombre, descripcion, estado)
            VALUES (:nombre, :descripcion, :estado)
            RETURNING id_categoria, nombre, descripcion, estado
        """),
        values,
    ).mappings().one()
    return dict(row)


def update_category(
    db: Session,
    id_categoria: int,
    values: dict[str, Any],
) -> dict[str, Any] | None:
    allowed = {"nombre", "descripcion", "estado"}
    if not values:
        return get_category(db, id_categoria)
    if not values.keys() <= allowed:
        raise ValueError("Invalid category fields")
    assignments = ", ".join(f"{key} = :{key}" for key in values)
    row = db.execute(
        text(f"""
            UPDATE catalogo.categorias
            SET {assignments}
            WHERE id_categoria = :id_categoria
            RETURNING id_categoria, nombre, descripcion, estado
        """),
        {**values, "id_categoria": id_categoria},
    ).mappings().first()
    return dict(row) if row is not None else None


def list_products(
    db: Session,
    *,
    estado: str,
    id_categoria: int | None,
    search: str | None,
    limit: int,
    offset: int,
) -> list[dict[str, Any]]:
    conditions = ["estado = :estado"]
    parameters: dict[str, Any] = {
        "estado": estado,
        "limit": limit,
        "offset": offset,
    }

    if id_categoria is not None:
        conditions.append("id_categoria = :id_categoria")
        parameters["id_categoria"] = id_categoria
    if search is not None:
        conditions.append("(sku ILIKE :search OR nombre ILIKE :search)")
        parameters["search"] = f"%{search}%"

    result = db.execute(
        text(f"""
            SELECT id_producto, sku, nombre, id_categoria, unidad_medida,
                   precio_lista, estado
            FROM catalogo.productos
            WHERE {' AND '.join(conditions)}
            ORDER BY id_producto
            LIMIT :limit OFFSET :offset
        """),
        parameters,
    )
    return [dict(row) for row in result.mappings().all()]


def get_product(db: Session, id_producto: int) -> dict[str, Any] | None:
    row = db.execute(
        text("""
            SELECT id_producto, sku, nombre, id_categoria, unidad_medida,
                   precio_lista, estado
            FROM catalogo.productos
            WHERE id_producto = :id_producto
        """),
        {"id_producto": id_producto},
    ).mappings().first()
    return dict(row) if row is not None else None


def create_product(db: Session, values: dict[str, Any]) -> dict[str, Any]:
    row = db.execute(
        text("""
            INSERT INTO catalogo.productos
                (sku, nombre, id_categoria, unidad_medida, precio_lista, estado)
            VALUES
                (:sku, :nombre, :id_categoria, :unidad_medida, :precio_lista, :estado)
            RETURNING id_producto, sku, nombre, id_categoria, unidad_medida,
                      precio_lista, estado
        """),
        values,
    ).mappings().one()
    return dict(row)


def update_product(
    db: Session,
    id_producto: int,
    values: dict[str, Any],
) -> dict[str, Any] | None:
    allowed = {
        "sku",
        "nombre",
        "id_categoria",
        "unidad_medida",
        "precio_lista",
        "estado",
    }
    if not values:
        return get_product(db, id_producto)
    if not values.keys() <= allowed:
        raise ValueError("Invalid product fields")
    assignments = ", ".join(f"{key} = :{key}" for key in values)
    row = db.execute(
        text(f"""
            UPDATE catalogo.productos
            SET {assignments}
            WHERE id_producto = :id_producto
            RETURNING id_producto, sku, nombre, id_categoria, unidad_medida,
                      precio_lista, estado
        """),
        {**values, "id_producto": id_producto},
    ).mappings().first()
    return dict(row) if row is not None else None
