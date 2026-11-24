from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def list_inventory(
    db: Session,
    *,
    id_producto: int | None,
    id_sede: int | None,
    id_almacen: int | None,
    below_minimum: bool | None,
    limit: int,
    offset: int,
) -> list[dict[str, Any]]:
    conditions: list[str] = []
    parameters: dict[str, Any] = {"limit": limit, "offset": offset}
    for column, value in (
        ("id_producto", id_producto),
        ("id_sede", id_sede),
        ("id_almacen", id_almacen),
    ):
        if value is not None:
            conditions.append(f"{column} = :{column}")
            parameters[column] = value
    if below_minimum is True:
        conditions.append("existencia_actual <= stock_minimo")
    elif below_minimum is False:
        conditions.append("existencia_actual > stock_minimo")
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    rows = db.execute(
        text(f"""
            SELECT id_almacen, id_producto, id_sede, existencia_actual,
                   stock_minimo, fecha_actualizacion
            FROM inventarios.inventarios
            {where_clause}
            ORDER BY id_sede, id_almacen NULLS FIRST, id_producto
            LIMIT :limit OFFSET :offset
        """),
        parameters,
    ).mappings().all()
    return [dict(row) for row in rows]


def update_stock_minimum(
    db: Session,
    *,
    id_almacen: int,
    id_producto: int,
    stock_minimo: int,
) -> dict[str, Any] | None:
    row = db.execute(
        text("""
            UPDATE inventarios.inventarios
            SET stock_minimo = :stock_minimo,
                fecha_actualizacion = CURRENT_TIMESTAMP
            WHERE id_almacen = :id_almacen
              AND id_producto = :id_producto
            RETURNING id_almacen, id_producto, id_sede, existencia_actual,
                      stock_minimo, fecha_actualizacion
        """),
        {
            "id_almacen": id_almacen,
            "id_producto": id_producto,
            "stock_minimo": stock_minimo,
        },
    ).mappings().first()
    return dict(row) if row is not None else None


def list_transfers(
    db: Session,
    *,
    estado: str | None,
    id_almacen: int | None,
    limit: int,
    offset: int,
) -> list[dict[str, Any]]:
    conditions: list[str] = []
    parameters: dict[str, Any] = {"limit": limit, "offset": offset}
    if estado is not None:
        conditions.append("estado = :estado")
        parameters["estado"] = estado
    if id_almacen is not None:
        conditions.append(
            "(id_almacen_origen = :id_almacen OR id_almacen_destino = :id_almacen)"
        )
        parameters["id_almacen"] = id_almacen
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    rows = db.execute(
        text(f"""
            SELECT id_transferencia, id_almacen_origen, id_almacen_destino,
                   fecha_solicitud, fecha_despacho, fecha_recepcion, estado
            FROM inventarios.transferencias
            {where_clause}
            ORDER BY id_transferencia DESC
            LIMIT :limit OFFSET :offset
        """),
        parameters,
    ).mappings().all()
    return [dict(row) for row in rows]


def get_transfer(db: Session, id_transferencia: int) -> dict[str, Any] | None:
    row = db.execute(
        text("""
            SELECT id_transferencia, id_almacen_origen, id_almacen_destino,
                   fecha_solicitud, fecha_despacho, fecha_recepcion, estado
            FROM inventarios.transferencias
            WHERE id_transferencia = :id_transferencia
        """),
        {"id_transferencia": id_transferencia},
    ).mappings().first()
    return dict(row) if row is not None else None


def list_transfer_details(
    db: Session,
    id_transferencia: int,
) -> list[dict[str, Any]]:
    rows = db.execute(
        text("""
            SELECT id_transferencia, id_producto, cantidad_enviada, cantidad_recibida
            FROM inventarios.detalle_transferencia
            WHERE id_transferencia = :id_transferencia
            ORDER BY id_producto
        """),
        {"id_transferencia": id_transferencia},
    ).mappings().all()
    return [dict(row) for row in rows]
