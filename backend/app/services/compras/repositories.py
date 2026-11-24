from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


SUPPLIER_COLUMNS = {
    "identificacion",
    "razon_social",
    "ciudad",
    "correo",
    "telefono",
    "estado",
}


def list_suppliers(
    db: Session,
    *,
    estado: str | None,
    search: str | None,
    limit: int,
    offset: int,
) -> list[dict[str, Any]]:
    conditions: list[str] = []
    parameters: dict[str, Any] = {"limit": limit, "offset": offset}
    if estado is not None:
        conditions.append("estado = :estado")
        parameters["estado"] = estado
    if search is not None:
        conditions.append(
            "(identificacion ILIKE :search OR razon_social ILIKE :search)"
        )
        parameters["search"] = f"%{search}%"
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    rows = db.execute(
        text(f"""
            SELECT id_proveedor, identificacion, razon_social, ciudad,
                   correo, telefono, estado
            FROM compras.proveedores
            {where_clause}
            ORDER BY id_proveedor
            LIMIT :limit OFFSET :offset
        """),
        parameters,
    ).mappings().all()
    return [dict(row) for row in rows]


def get_supplier(db: Session, id_proveedor: int) -> dict[str, Any] | None:
    row = db.execute(
        text("""
            SELECT id_proveedor, identificacion, razon_social, ciudad,
                   correo, telefono, estado
            FROM compras.proveedores
            WHERE id_proveedor = :id_proveedor
        """),
        {"id_proveedor": id_proveedor},
    ).mappings().first()
    return dict(row) if row is not None else None


def get_product_supplier(
    db: Session,
    *,
    id_producto: int,
    id_proveedor: int,
) -> dict[str, Any] | None:
    row = db.execute(
        text("""
            SELECT id_producto, id_proveedor, costo_referencia, estado
            FROM compras.producto_proveedor
            WHERE id_producto = :id_producto
              AND id_proveedor = :id_proveedor
        """),
        {"id_producto": id_producto, "id_proveedor": id_proveedor},
    ).mappings().first()
    return dict(row) if row is not None else None


def create_purchase_order(
    db: Session,
    *,
    id_proveedor: int,
    id_almacen_destino: int,
    id_empleado_creador: int,
    fecha_estimada: Any,
    products: list[dict[str, Any]],
) -> dict[str, Any]:
    order = db.execute(
        text("""
            INSERT INTO compras.ordenes_compra
                (id_proveedor, id_almacen_destino, id_empleado_creador,
                 fecha_estimada, estado)
            VALUES
                (:id_proveedor, :id_almacen_destino, :id_empleado_creador,
                 :fecha_estimada, 'pendiente')
            RETURNING id_orden_compra, id_proveedor, id_almacen_destino,
                      id_empleado_creador, fecha_orden, fecha_estimada, estado
        """),
        {
            "id_proveedor": id_proveedor,
            "id_almacen_destino": id_almacen_destino,
            "id_empleado_creador": id_empleado_creador,
            "fecha_estimada": fecha_estimada,
        },
    ).mappings().one()
    for product in products:
        db.execute(
            text("""
                INSERT INTO compras.detalle_orden_compra
                    (id_orden_compra, id_producto, cantidad_solicitada, costo_unitario)
                VALUES
                    (:id_orden_compra, :id_producto, :cantidad_solicitada, :costo_unitario)
            """),
            {
                "id_orden_compra": order["id_orden_compra"],
                **product,
            },
        )
    return dict(order)


def register_purchase_receipt(
    db: Session,
    *,
    id_orden_compra: int,
    received_totals: dict[int, int],
) -> dict[str, Any] | None:
    order = db.execute(
        text("""
            SELECT id_orden_compra, estado
            FROM compras.ordenes_compra
            WHERE id_orden_compra = :id_orden_compra
            FOR UPDATE
        """),
        {"id_orden_compra": id_orden_compra},
    ).mappings().first()
    if order is None:
        return None
    if order["estado"] not in ("pendiente", "recibida_parcial"):
        raise ValueError("La orden no admite más recepciones")

    details = list_purchase_order_details(db, id_orden_compra)
    details_by_product = {row["id_producto"]: row for row in details}
    deltas: dict[int, int] = {}
    totals: dict[int, int] = {
        row["id_producto"]: row["cantidad_recibida"] for row in details
    }
    for id_producto, total in received_totals.items():
        detail = details_by_product.get(id_producto)
        if detail is None:
            raise ValueError("El producto no pertenece a la orden")
        if total < detail["cantidad_recibida"]:
            raise ValueError("La cantidad recibida acumulada no puede disminuir")
        if total > detail["cantidad_solicitada"]:
            raise ValueError("La cantidad recibida supera la solicitada")
        delta = total - detail["cantidad_recibida"]
        if delta:
            deltas[id_producto] = delta
        totals[id_producto] = total

    if not deltas:
        return {
            "id_recepcion": None,
            "id_orden_compra": id_orden_compra,
            "fecha_recepcion": None,
            "estado": "procesada",
            "cantidades_actualizadas": False,
        }

    receipt = db.execute(
        text("""
            INSERT INTO compras.recepciones_compra (id_orden_compra, estado)
            VALUES (:id_orden_compra, 'procesada')
            RETURNING id_recepcion, id_orden_compra, fecha_recepcion, estado
        """),
        {"id_orden_compra": id_orden_compra},
    ).mappings().one()
    for id_producto, quantity in deltas.items():
        db.execute(
            text("""
                INSERT INTO compras.detalle_recepcion
                    (id_recepcion, id_producto, cantidad_recibida)
                VALUES (:id_recepcion, :id_producto, :cantidad_recibida)
            """),
            {
                "id_recepcion": receipt["id_recepcion"],
                "id_producto": id_producto,
                "cantidad_recibida": quantity,
            },
        )

    completed = all(
        totals.get(row["id_producto"], row["cantidad_recibida"])
        == row["cantidad_solicitada"]
        for row in details
    )
    db.execute(
        text("""
            UPDATE compras.ordenes_compra
            SET estado = :estado
            WHERE id_orden_compra = :id_orden_compra
        """),
        {
            "id_orden_compra": id_orden_compra,
            "estado": "completada" if completed else "recibida_parcial",
        },
    )
    return {**dict(receipt), "cantidades_actualizadas": True}


def create_supplier(db: Session, values: dict[str, Any]) -> dict[str, Any]:
    row = db.execute(
        text("""
            INSERT INTO compras.proveedores
                (identificacion, razon_social, ciudad, correo, telefono, estado)
            VALUES
                (:identificacion, :razon_social, :ciudad, :correo, :telefono, :estado)
            RETURNING id_proveedor, identificacion, razon_social, ciudad,
                      correo, telefono, estado
        """),
        values,
    ).mappings().one()
    return dict(row)


def update_supplier(
    db: Session,
    id_proveedor: int,
    values: dict[str, Any],
) -> dict[str, Any] | None:
    if not values:
        return get_supplier(db, id_proveedor)
    if not values.keys() <= SUPPLIER_COLUMNS:
        raise ValueError("Invalid supplier fields")
    assignments = ", ".join(f"{key} = :{key}" for key in values)
    row = db.execute(
        text(f"""
            UPDATE compras.proveedores
            SET {assignments}
            WHERE id_proveedor = :id_proveedor
            RETURNING id_proveedor, identificacion, razon_social, ciudad,
                      correo, telefono, estado
        """),
        {**values, "id_proveedor": id_proveedor},
    ).mappings().first()
    return dict(row) if row is not None else None


def list_product_suppliers(
    db: Session,
    *,
    id_producto: int | None,
    id_proveedor: int | None,
    estado: str | None,
    limit: int,
    offset: int,
) -> list[dict[str, Any]]:
    conditions: list[str] = []
    parameters: dict[str, Any] = {"limit": limit, "offset": offset}
    for column, value in (
        ("id_producto", id_producto),
        ("id_proveedor", id_proveedor),
        ("estado", estado),
    ):
        if value is not None:
            conditions.append(f"{column} = :{column}")
            parameters[column] = value
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    rows = db.execute(
        text(f"""
            SELECT id_producto, id_proveedor, costo_referencia,
                   plazo_entrega_dias, estado
            FROM compras.producto_proveedor
            {where_clause}
            ORDER BY id_proveedor, id_producto
            LIMIT :limit OFFSET :offset
        """),
        parameters,
    ).mappings().all()
    return [dict(row) for row in rows]


def upsert_product_supplier(
    db: Session,
    *,
    id_producto: int,
    id_proveedor: int,
    values: dict[str, Any],
) -> dict[str, Any]:
    row = db.execute(
        text("""
            INSERT INTO compras.producto_proveedor
                (id_producto, id_proveedor, costo_referencia,
                 plazo_entrega_dias, estado)
            VALUES
                (:id_producto, :id_proveedor, :costo_referencia,
                 :plazo_entrega_dias, :estado)
            ON CONFLICT (id_producto, id_proveedor)
            DO UPDATE SET
                costo_referencia = EXCLUDED.costo_referencia,
                plazo_entrega_dias = EXCLUDED.plazo_entrega_dias,
                estado = EXCLUDED.estado
            RETURNING id_producto, id_proveedor, costo_referencia,
                      plazo_entrega_dias, estado
        """),
        {
            "id_producto": id_producto,
            "id_proveedor": id_proveedor,
            **values,
        },
    ).mappings().one()
    return dict(row)


def deactivate_product_supplier(
    db: Session,
    *,
    id_producto: int,
    id_proveedor: int,
) -> dict[str, Any] | None:
    row = db.execute(
        text("""
            UPDATE compras.producto_proveedor
            SET estado = 'inactivo'
            WHERE id_producto = :id_producto
              AND id_proveedor = :id_proveedor
            RETURNING id_producto, id_proveedor, costo_referencia,
                      plazo_entrega_dias, estado
        """),
        {"id_producto": id_producto, "id_proveedor": id_proveedor},
    ).mappings().first()
    return dict(row) if row is not None else None


def list_purchase_orders(
    db: Session,
    *,
    id_proveedor: int | None,
    id_almacen_destino: int | None,
    id_empleado_creador: int | None,
    estado: str | None,
    limit: int,
    offset: int,
) -> list[dict[str, Any]]:
    conditions: list[str] = []
    parameters: dict[str, Any] = {"limit": limit, "offset": offset}
    for column, value in (
        ("id_proveedor", id_proveedor),
        ("id_almacen_destino", id_almacen_destino),
        ("id_empleado_creador", id_empleado_creador),
        ("estado", estado),
    ):
        if value is not None:
            conditions.append(f"{column} = :{column}")
            parameters[column] = value
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    rows = db.execute(
        text(f"""
            SELECT id_orden_compra, id_proveedor, id_almacen_destino,
                   id_empleado_creador, fecha_orden, fecha_estimada, estado
            FROM compras.ordenes_compra
            {where_clause}
            ORDER BY fecha_orden DESC, id_orden_compra DESC
            LIMIT :limit OFFSET :offset
        """),
        parameters,
    ).mappings().all()
    return [dict(row) for row in rows]


def get_purchase_order(
    db: Session,
    id_orden_compra: int,
) -> dict[str, Any] | None:
    row = db.execute(
        text("""
            SELECT id_orden_compra, id_proveedor, id_almacen_destino,
                   id_empleado_creador, fecha_orden, fecha_estimada, estado
            FROM compras.ordenes_compra
            WHERE id_orden_compra = :id_orden_compra
        """),
        {"id_orden_compra": id_orden_compra},
    ).mappings().first()
    return dict(row) if row is not None else None


def list_purchase_order_details(
    db: Session,
    id_orden_compra: int,
) -> list[dict[str, Any]]:
    rows = db.execute(
        text("""
            SELECT d.id_orden_compra, d.id_producto, d.cantidad_solicitada,
                   d.costo_unitario,
                   COALESCE(SUM(dr.cantidad_recibida), 0)::integer
                       AS cantidad_recibida,
                   (d.cantidad_solicitada
                    - COALESCE(SUM(dr.cantidad_recibida), 0))::integer
                       AS cantidad_pendiente
            FROM compras.detalle_orden_compra AS d
            LEFT JOIN compras.recepciones_compra AS r
              ON r.id_orden_compra = d.id_orden_compra
             AND r.estado = 'procesada'
            LEFT JOIN compras.detalle_recepcion AS dr
              ON dr.id_recepcion = r.id_recepcion
             AND dr.id_producto = d.id_producto
            WHERE d.id_orden_compra = :id_orden_compra
            GROUP BY d.id_orden_compra, d.id_producto,
                     d.cantidad_solicitada, d.costo_unitario
            ORDER BY d.id_producto
        """),
        {"id_orden_compra": id_orden_compra},
    ).mappings().all()
    return [dict(row) for row in rows]


def cancel_purchase_order(
    db: Session,
    id_orden_compra: int,
) -> dict[str, Any] | None:
    row = db.execute(
        text("""
            UPDATE compras.ordenes_compra
            SET estado = 'cancelada'
            WHERE id_orden_compra = :id_orden_compra
              AND estado = 'pendiente'
            RETURNING id_orden_compra, id_proveedor, id_almacen_destino,
                      id_empleado_creador, fecha_orden, fecha_estimada, estado
        """),
        {"id_orden_compra": id_orden_compra},
    ).mappings().first()
    return dict(row) if row is not None else None


def list_receipts(
    db: Session,
    *,
    id_orden_compra: int | None,
    estado: str | None,
    limit: int,
    offset: int,
) -> list[dict[str, Any]]:
    conditions: list[str] = []
    parameters: dict[str, Any] = {"limit": limit, "offset": offset}
    if id_orden_compra is not None:
        conditions.append("id_orden_compra = :id_orden_compra")
        parameters["id_orden_compra"] = id_orden_compra
    if estado is not None:
        conditions.append("estado = :estado")
        parameters["estado"] = estado
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    rows = db.execute(
        text(f"""
            SELECT id_recepcion, id_orden_compra, fecha_recepcion, estado
            FROM compras.recepciones_compra
            {where_clause}
            ORDER BY fecha_recepcion DESC, id_recepcion DESC
            LIMIT :limit OFFSET :offset
        """),
        parameters,
    ).mappings().all()
    return [dict(row) for row in rows]


def get_receipt(db: Session, id_recepcion: int) -> dict[str, Any] | None:
    row = db.execute(
        text("""
            SELECT id_recepcion, id_orden_compra, fecha_recepcion, estado
            FROM compras.recepciones_compra
            WHERE id_recepcion = :id_recepcion
        """),
        {"id_recepcion": id_recepcion},
    ).mappings().first()
    return dict(row) if row is not None else None


def list_receipt_details(db: Session, id_recepcion: int) -> list[dict[str, Any]]:
    rows = db.execute(
        text("""
            SELECT id_recepcion, id_producto, cantidad_recibida
            FROM compras.detalle_recepcion
            WHERE id_recepcion = :id_recepcion
            ORDER BY id_producto
        """),
        {"id_recepcion": id_recepcion},
    ).mappings().all()
    return [dict(row) for row in rows]
