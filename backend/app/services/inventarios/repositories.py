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


def adjust_inventory(
    db: Session,
    *,
    id_almacen: int,
    id_producto: int,
    id_sede: int,
    existencia_objetivo: int,
) -> dict[str, Any] | None:
    db.execute(
        text("""
            SELECT id_almacen
            FROM inventarios.inventarios
            WHERE id_almacen = :id_almacen
              AND id_producto = :id_producto
            FOR UPDATE
        """),
        {"id_almacen": id_almacen, "id_producto": id_producto},
    ).first()
    row = db.execute(
        text("""
            INSERT INTO inventarios.inventarios
                (id_almacen, id_producto, id_sede, existencia_actual)
            VALUES
                (:id_almacen, :id_producto, :id_sede, :existencia_objetivo)
            ON CONFLICT (id_almacen, id_producto)
            DO UPDATE SET
                existencia_actual = EXCLUDED.existencia_actual,
                id_sede = EXCLUDED.id_sede,
                fecha_actualizacion = CURRENT_TIMESTAMP
            RETURNING id_almacen, id_producto, id_sede, existencia_actual,
                      stock_minimo, fecha_actualizacion
        """),
        {
            "id_almacen": id_almacen,
            "id_producto": id_producto,
            "id_sede": id_sede,
            "existencia_objetivo": existencia_objetivo,
        },
    ).mappings().first()
    return dict(row) if row is not None else None


def create_transfer(
    db: Session,
    *,
    id_almacen_origen: int,
    id_almacen_destino: int,
    products: list[dict[str, int]],
) -> dict[str, Any]:
    transfer = db.execute(
        text("""
            INSERT INTO inventarios.transferencias
                (id_almacen_origen, id_almacen_destino, estado)
            VALUES (:id_almacen_origen, :id_almacen_destino, 'solicitada')
            RETURNING id_transferencia, id_almacen_origen, id_almacen_destino,
                      fecha_solicitud, fecha_despacho, fecha_recepcion, estado
        """),
        {
            "id_almacen_origen": id_almacen_origen,
            "id_almacen_destino": id_almacen_destino,
        },
    ).mappings().one()
    for product in products:
        db.execute(
            text("""
                INSERT INTO inventarios.detalle_transferencia
                    (id_transferencia, id_producto, cantidad_enviada)
                VALUES (:id_transferencia, :id_producto, :cantidad_enviada)
            """),
            {"id_transferencia": transfer["id_transferencia"], **product},
        )
    return dict(transfer)


def dispatch_transfer(db: Session, id_transferencia: int) -> dict[str, Any] | None:
    transfer = db.execute(
        text("""
            SELECT id_transferencia, id_almacen_origen, estado
            FROM inventarios.transferencias
            WHERE id_transferencia = :id_transferencia
            FOR UPDATE
        """),
        {"id_transferencia": id_transferencia},
    ).mappings().first()
    if transfer is None:
        return None
    if transfer["estado"] != "solicitada":
        raise ValueError("Solo se pueden despachar transferencias solicitadas")

    details = db.execute(
        text("""
            SELECT id_producto, cantidad_enviada
            FROM inventarios.detalle_transferencia
            WHERE id_transferencia = :id_transferencia
            ORDER BY id_producto
            FOR UPDATE
        """),
        {"id_transferencia": id_transferencia},
    ).mappings().all()
    if not details:
        raise ValueError("La transferencia no tiene productos")
    for detail in details:
        stock = db.execute(
            text("""
                SELECT existencia_actual
                FROM inventarios.inventarios
                WHERE id_almacen = :id_almacen
                  AND id_producto = :id_producto
                FOR UPDATE
            """),
            {
                "id_almacen": transfer["id_almacen_origen"],
                "id_producto": detail["id_producto"],
            },
        ).mappings().first()
        if stock is None or stock["existencia_actual"] < detail["cantidad_enviada"]:
            raise ValueError(f"Existencias insuficientes para el producto {detail['id_producto']}")

    for detail in details:
        db.execute(
            text("""
                UPDATE inventarios.inventarios
                SET existencia_actual = existencia_actual - :cantidad,
                    fecha_actualizacion = CURRENT_TIMESTAMP
                WHERE id_almacen = :id_almacen
                  AND id_producto = :id_producto
            """),
            {
                "id_almacen": transfer["id_almacen_origen"],
                "id_producto": detail["id_producto"],
                "cantidad": detail["cantidad_enviada"],
            },
        )
        db.execute(
            text("""
                UPDATE inventarios.detalle_transferencia
                SET cantidad_recibida = 0
                WHERE id_transferencia = :id_transferencia
                  AND id_producto = :id_producto
            """),
            {
                "id_transferencia": id_transferencia,
                "id_producto": detail["id_producto"],
            },
        )
    row = db.execute(
        text("""
            UPDATE inventarios.transferencias
            SET estado = 'despachada', fecha_despacho = CURRENT_TIMESTAMP
            WHERE id_transferencia = :id_transferencia
            RETURNING id_transferencia, id_almacen_origen, id_almacen_destino,
                      fecha_solicitud, fecha_despacho, fecha_recepcion, estado
        """),
        {"id_transferencia": id_transferencia},
    ).mappings().one()
    return dict(row)


def receive_transfer(
    db: Session,
    *,
    id_transferencia: int,
    id_sede_destino: int,
    received_totals: dict[int, int],
) -> dict[str, Any] | None:
    transfer = db.execute(
        text("""
            SELECT id_transferencia, id_almacen_destino, estado
            FROM inventarios.transferencias
            WHERE id_transferencia = :id_transferencia
            FOR UPDATE
        """),
        {"id_transferencia": id_transferencia},
    ).mappings().first()
    if transfer is None:
        return None
    if transfer["estado"] != "despachada":
        raise ValueError("Solo se pueden recibir transferencias despachadas")

    details = db.execute(
        text("""
            SELECT id_producto, cantidad_enviada,
                   COALESCE(cantidad_recibida, 0) AS cantidad_recibida
            FROM inventarios.detalle_transferencia
            WHERE id_transferencia = :id_transferencia
            ORDER BY id_producto
            FOR UPDATE
        """),
        {"id_transferencia": id_transferencia},
    ).mappings().all()
    details_by_product = {row["id_producto"]: row for row in details}
    new_totals = {
        row["id_producto"]: row["cantidad_recibida"] for row in details
    }
    deltas: dict[int, int] = {}
    for id_producto, total in received_totals.items():
        detail = details_by_product.get(id_producto)
        if detail is None:
            raise ValueError("El producto no pertenece a la transferencia")
        if total < detail["cantidad_recibida"]:
            raise ValueError("La cantidad recibida acumulada no puede disminuir")
        if total > detail["cantidad_enviada"]:
            raise ValueError("La cantidad recibida supera la cantidad enviada")
        delta = total - detail["cantidad_recibida"]
        if delta:
            deltas[id_producto] = delta
        new_totals[id_producto] = total

    for id_producto in sorted(deltas):
        delta = deltas[id_producto]
        inventory = db.execute(
            text("""
                SELECT existencia_actual
                FROM inventarios.inventarios
                WHERE id_almacen = :id_almacen
                  AND id_producto = :id_producto
                FOR UPDATE
            """),
            {
                "id_almacen": transfer["id_almacen_destino"],
                "id_producto": id_producto,
            },
        ).mappings().first()
        if inventory is None:
            db.execute(
                text("""
                    INSERT INTO inventarios.inventarios
                        (id_almacen, id_producto, id_sede, existencia_actual)
                    VALUES (:id_almacen, :id_producto, :id_sede, :delta)
                    ON CONFLICT (id_almacen, id_producto)
                    DO UPDATE SET
                        existencia_actual = inventarios.inventarios.existencia_actual
                            + EXCLUDED.existencia_actual,
                        id_sede = EXCLUDED.id_sede,
                        fecha_actualizacion = CURRENT_TIMESTAMP
                """),
                {
                    "id_almacen": transfer["id_almacen_destino"],
                    "id_producto": id_producto,
                    "id_sede": id_sede_destino,
                    "delta": delta,
                },
            )
        else:
            db.execute(
                text("""
                    UPDATE inventarios.inventarios
                    SET existencia_actual = existencia_actual + :delta,
                        id_sede = :id_sede,
                        fecha_actualizacion = CURRENT_TIMESTAMP
                    WHERE id_almacen = :id_almacen
                      AND id_producto = :id_producto
                """),
                {
                    "id_almacen": transfer["id_almacen_destino"],
                    "id_producto": id_producto,
                    "id_sede": id_sede_destino,
                    "delta": delta,
                },
            )
        db.execute(
            text("""
                UPDATE inventarios.detalle_transferencia
                SET cantidad_recibida = :cantidad_recibida
                WHERE id_transferencia = :id_transferencia
                  AND id_producto = :id_producto
            """),
            {
                "id_transferencia": id_transferencia,
                "id_producto": id_producto,
                "cantidad_recibida": new_totals[id_producto],
            },
        )

    completed = all(
        new_totals[row["id_producto"]] == row["cantidad_enviada"]
        for row in details
    )
    row = db.execute(
        text("""
            UPDATE inventarios.transferencias
            SET estado = :estado,
                fecha_recepcion = CASE
                    WHEN :completed THEN CURRENT_TIMESTAMP
                    ELSE fecha_recepcion
                END
            WHERE id_transferencia = :id_transferencia
            RETURNING id_transferencia, id_almacen_origen, id_almacen_destino,
                      fecha_solicitud, fecha_despacho, fecha_recepcion, estado
        """),
        {
            "id_transferencia": id_transferencia,
            "estado": "completada" if completed else "despachada",
            "completed": completed,
        },
    ).mappings().one()
    return dict(row)


def cancel_transfer(db: Session, id_transferencia: int) -> dict[str, Any] | None:
    row = db.execute(
        text("""
            UPDATE inventarios.transferencias
            SET estado = 'cancelada'
            WHERE id_transferencia = :id_transferencia
              AND estado = 'solicitada'
            RETURNING id_transferencia, id_almacen_origen, id_almacen_destino,
                      fecha_solicitud, fecha_despacho, fecha_recepcion, estado
        """),
        {"id_transferencia": id_transferencia},
    ).mappings().first()
    return dict(row) if row is not None else None


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




def dispatch_sales_order(
    db: Session,
    *,
    id_pedido: int,
    id_sede: int,
    id_almacen: int,
    products: list[dict[str, int]],
) -> dict[str, Any]:
    import json

    normalized_products = sorted(
        [
            {
                "id_producto": product["id_producto"],
                "cantidad": product["cantidad"],
            }
            for product in products
        ],
        key=lambda item: item["id_producto"],
    )

    products_json = json.dumps(normalized_products)

    inserted = db.execute(
        text("""
            INSERT INTO inventarios.despachos_venta (
                id_pedido,
                id_sede,
                id_almacen,
                productos
            )
            VALUES (
                :id_pedido,
                :id_sede,
                :id_almacen,
                CAST(:productos AS JSONB)
            )
            ON CONFLICT (id_pedido) DO NOTHING
            RETURNING id_pedido
        """),
        {
            "id_pedido": id_pedido,
            "id_sede": id_sede,
            "id_almacen": id_almacen,
            "productos": products_json,
        },
    ).scalar_one_or_none()

    if inserted is None:
        existing = db.execute(
            text("""
                SELECT id_sede, id_almacen, productos
                FROM inventarios.despachos_venta
                WHERE id_pedido = :id_pedido
            """),
            {"id_pedido": id_pedido},
        ).mappings().one()

        existing_products = sorted(
            existing["productos"],
            key=lambda item: item["id_producto"],
        )

        if (
            existing["id_sede"] != id_sede
            or existing["id_almacen"] != id_almacen
            or existing_products != normalized_products
        ):
            raise ValueError(
                "El pedido ya fue despachado con datos diferentes"
            )

        return {
            "id_pedido": id_pedido,
            "id_sede": id_sede,
            "id_almacen": id_almacen,
            "productos": normalized_products,
            "already_dispatched": True,
        }

    for product in normalized_products:
        stock = db.execute(
            text("""
                SELECT existencia_actual
                FROM inventarios.inventarios
                WHERE id_sede = :id_sede
                  AND id_almacen = :id_almacen
                  AND id_producto = :id_producto
                FOR UPDATE
            """),
            {
                "id_sede": id_sede,
                "id_almacen": id_almacen,
                "id_producto": product["id_producto"],
            },
        ).mappings().first()

        if (
            stock is None
            or stock["existencia_actual"] < product["cantidad"]
        ):
            raise ValueError(
                f"Existencias insuficientes para el producto "
                f"{product['id_producto']}"
            )

    for product in normalized_products:
        db.execute(
            text("""
                UPDATE inventarios.inventarios
                SET existencia_actual = existencia_actual - :cantidad,
                    fecha_actualizacion = CURRENT_TIMESTAMP
                WHERE id_sede = :id_sede
                  AND id_almacen = :id_almacen
                  AND id_producto = :id_producto
            """),
            {
                "id_sede": id_sede,
                "id_almacen": id_almacen,
                "id_producto": product["id_producto"],
                "cantidad": product["cantidad"],
            },
        )

    return {
        "id_pedido": id_pedido,
        "id_sede": id_sede,
        "id_almacen": id_almacen,
        "productos": normalized_products,
        "already_dispatched": False,
    }


def register_sales_return(
    db: Session,
    *,
    id_devolucion: int,
    id_pedido: int,
    id_sede: int,
    id_almacen: int,
    products: list[dict[str, int]],
) -> dict[str, Any]:
    import json

    normalized_products = sorted(
        [
            {
                "id_producto": product["id_producto"],
                "cantidad": product["cantidad"],
            }
            for product in products
        ],
        key=lambda item: item["id_producto"],
    )
    products_json = json.dumps(normalized_products)

    inserted = db.execute(
        text("""
            INSERT INTO inventarios.devoluciones_venta (
                id_devolucion,
                id_pedido,
                id_sede,
                id_almacen,
                productos
            )
            VALUES (
                :id_devolucion,
                :id_pedido,
                :id_sede,
                :id_almacen,
                CAST(:productos AS JSONB)
            )
            ON CONFLICT (id_devolucion) DO NOTHING
            RETURNING id_devolucion
        """),
        {
            "id_devolucion": id_devolucion,
            "id_pedido": id_pedido,
            "id_sede": id_sede,
            "id_almacen": id_almacen,
            "productos": products_json,
        },
    ).scalar_one_or_none()

    if inserted is None:
        existing = db.execute(
            text("""
                SELECT id_pedido, id_sede, id_almacen, productos
                FROM inventarios.devoluciones_venta
                WHERE id_devolucion = :id_devolucion
            """),
            {"id_devolucion": id_devolucion},
        ).mappings().one()
        existing_products = sorted(
            existing["productos"],
            key=lambda item: item["id_producto"],
        )
        if (
            existing["id_pedido"] != id_pedido
            or existing["id_sede"] != id_sede
            or existing["id_almacen"] != id_almacen
            or existing_products != normalized_products
        ):
            raise ValueError(
                "La devolución ya fue procesada con datos diferentes"
            )

        return {
            "id_devolucion": id_devolucion,
            "id_pedido": id_pedido,
            "id_sede": id_sede,
            "id_almacen": id_almacen,
            "productos": normalized_products,
            "already_returned": True,
        }

    for product in normalized_products:
        updated = db.execute(
            text("""
                UPDATE inventarios.inventarios
                SET existencia_actual = existencia_actual + :cantidad,
                    fecha_actualizacion = CURRENT_TIMESTAMP
                WHERE id_sede = :id_sede
                  AND id_almacen = :id_almacen
                  AND id_producto = :id_producto
                RETURNING id_producto
            """),
            {
                "id_sede": id_sede,
                "id_almacen": id_almacen,
                "id_producto": product["id_producto"],
                "cantidad": product["cantidad"],
            },
        ).mappings().first()
        if updated is None:
            raise ValueError(
                f"No existe inventario para el producto "
                f"{product['id_producto']} en el almacén indicado"
            )

    return {
        "id_devolucion": id_devolucion,
        "id_pedido": id_pedido,
        "id_sede": id_sede,
        "id_almacen": id_almacen,
        "productos": normalized_products,
        "already_returned": False,
    }
