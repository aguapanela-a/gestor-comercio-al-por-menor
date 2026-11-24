from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

ORDER_FRAGMENTS = {
    1: "ventas.sede_norte_pedidos",
    2: "ventas.sede_sur_pedidos",
    3: "ventas.sede_centro_pedidos",
    4: "ventas.sede_distribucion_pedidos",
}
ORDER_FRAGMENT_BY_SITE = ORDER_FRAGMENTS

ORDER_UNION = " UNION ALL ".join(
    f"""
        SELECT id_pedido, id_sede, id_almacen, id_cliente, id_empleado,
               fecha_pedido, estado, total_registrado
        FROM {table}
    """
    for table in ORDER_FRAGMENTS.values()
)

CUSTOMER_COLUMNS = {
    "tipo_documento",
    "num_documento",
    "nombre_completo",
    "correo",
    "telefono",
    "estado",
}


def list_customers(
    db: Session,
    *,
    estado: str | None,
    num_documento: str | None,
    search: str | None,
    limit: int,
    offset: int,
) -> list[dict[str, Any]]:
    conditions: list[str] = []
    parameters: dict[str, Any] = {"limit": limit, "offset": offset}
    if estado is not None:
        conditions.append("estado = :estado")
        parameters["estado"] = estado
    if num_documento is not None:
        conditions.append("num_documento = :num_documento")
        parameters["num_documento"] = num_documento
    if search is not None:
        conditions.append("nombre_completo ILIKE :search")
        parameters["search"] = f"%{search}%"
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    rows = db.execute(
        text(f"""
            SELECT id_cliente, tipo_documento, num_documento, nombre_completo,
                   correo, telefono, estado
            FROM ventas.clientes
            {where_clause}
            ORDER BY id_cliente
            LIMIT :limit OFFSET :offset
        """),
        parameters,
    ).mappings().all()
    return [dict(row) for row in rows]


def get_customer(db: Session, id_cliente: int) -> dict[str, Any] | None:
    row = db.execute(
        text("""
            SELECT id_cliente, tipo_documento, num_documento, nombre_completo,
                   correo, telefono, estado
            FROM ventas.clientes
            WHERE id_cliente = :id_cliente
        """),
        {"id_cliente": id_cliente},
    ).mappings().first()
    return dict(row) if row is not None else None


def create_customer(db: Session, values: dict[str, Any]) -> dict[str, Any]:
    row = db.execute(
        text("""
            INSERT INTO ventas.clientes
                (tipo_documento, num_documento, nombre_completo,
                 correo, telefono, estado)
            VALUES
                (:tipo_documento, :num_documento, :nombre_completo,
                 :correo, :telefono, :estado)
            RETURNING id_cliente, tipo_documento, num_documento,
                      nombre_completo, correo, telefono, estado
        """),
        values,
    ).mappings().one()
    return dict(row)


def update_customer(
    db: Session,
    id_cliente: int,
    values: dict[str, Any],
) -> dict[str, Any] | None:
    if not values:
        return get_customer(db, id_cliente)
    if not values.keys() <= CUSTOMER_COLUMNS:
        raise ValueError("Invalid customer fields")
    assignments = ", ".join(f"{key} = :{key}" for key in values)
    row = db.execute(
        text(f"""
            UPDATE ventas.clientes
            SET {assignments}
            WHERE id_cliente = :id_cliente
            RETURNING id_cliente, tipo_documento, num_documento,
                      nombre_completo, correo, telefono, estado
        """),
        {**values, "id_cliente": id_cliente},
    ).mappings().first()
    return dict(row) if row is not None else None


def list_orders(
    db: Session,
    *,
    id_sede: int | None,
    id_almacen: int | None,
    id_cliente: int | None,
    id_empleado: int | None,
    estado: str | None,
    fecha_desde: date | None,
    fecha_hasta: date | None,
    limit: int,
    offset: int,
) -> list[dict[str, Any]]:
    conditions: list[str] = []
    parameters: dict[str, Any] = {"limit": limit, "offset": offset}
    for column, value in (
        ("id_sede", id_sede),
        ("id_almacen", id_almacen),
        ("id_cliente", id_cliente),
        ("id_empleado", id_empleado),
        ("estado", estado),
    ):
        if value is not None:
            conditions.append(f"{column} = :{column}")
            parameters[column] = value
    if fecha_desde is not None:
        conditions.append("fecha_pedido >= :fecha_desde")
        parameters["fecha_desde"] = fecha_desde
    if fecha_hasta is not None:
        conditions.append("fecha_pedido < (:fecha_hasta + INTERVAL '1 day')")
        parameters["fecha_hasta"] = fecha_hasta
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    rows = db.execute(
        text(f"""
            SELECT id_pedido, id_sede, id_almacen, id_cliente, id_empleado,
                   fecha_pedido, estado, total_registrado
            FROM ({ORDER_UNION}) AS pedidos_fragmentados
            {where_clause}
            ORDER BY fecha_pedido DESC, id_pedido DESC
            LIMIT :limit OFFSET :offset
        """),
        parameters,
    ).mappings().all()
    return [dict(row) for row in rows]


def get_order(db: Session, id_pedido: int) -> dict[str, Any] | None:
    row = db.execute(
        text(f"""
            SELECT id_pedido, id_sede, id_almacen, id_cliente, id_empleado,
                   fecha_pedido, estado, total_registrado
            FROM ({ORDER_UNION}) AS pedidos_fragmentados
            WHERE id_pedido = :id_pedido
        """),
        {"id_pedido": id_pedido},
    ).mappings().first()
    return dict(row) if row is not None else None


def lock_order(db: Session, id_pedido: int) -> dict[str, Any] | None:
    order = get_order(db, id_pedido)
    if order is None:
        return None
    table = ORDER_FRAGMENT_BY_SITE.get(order["id_sede"])
    if table is None:
        return None
    row = db.execute(
        text(f"""
            SELECT id_pedido, id_sede, id_almacen, id_cliente, id_empleado,
                   fecha_pedido, estado, total_registrado
            FROM {table}
            WHERE id_pedido = :id_pedido
            FOR UPDATE
        """),
        {"id_pedido": id_pedido},
    ).mappings().first()
    return dict(row) if row is not None else None


def create_order(
    db: Session,
    *,
    id_sede: int,
    id_almacen: int,
    id_cliente: int,
    id_empleado: int,
    products: list[dict[str, Any]],
) -> dict[str, Any]:
    table = ORDER_FRAGMENT_BY_SITE[id_sede]
    total = sum(
        product["cantidad"] * product["precio_unitario"]
        for product in products
    )
    order = db.execute(
        text(f"""
            INSERT INTO {table}
                (id_sede, id_almacen, id_cliente, id_empleado, estado,
                 total_registrado)
            VALUES
                (:id_sede, :id_almacen, :id_cliente, :id_empleado, 'pendiente',
                 :total_registrado)
            RETURNING id_pedido, id_sede, id_almacen, id_cliente, id_empleado,
                      fecha_pedido, estado, total_registrado
        """),
        {
            "id_sede": id_sede,
            "id_almacen": id_almacen,
            "id_cliente": id_cliente,
            "id_empleado": id_empleado,
            "total_registrado": total,
        },
    ).mappings().one()
    for product in products:
        db.execute(
            text("""
                INSERT INTO ventas.detalle_pedido
                    (id_pedido, id_producto, cantidad, precio_unitario)
                VALUES (:id_pedido, :id_producto, :cantidad, :precio_unitario)
            """),
            {"id_pedido": order["id_pedido"], **product},
        )
    return dict(order)


def list_order_details(db: Session, id_pedido: int) -> list[dict[str, Any]]:
    rows = db.execute(
        text("""
            SELECT id_pedido, id_producto, cantidad, precio_unitario
            FROM ventas.detalle_pedido
            WHERE id_pedido = :id_pedido
            ORDER BY id_producto
        """),
        {"id_pedido": id_pedido},
    ).mappings().all()
    return [dict(row) for row in rows]


def order_balance(db: Session, id_pedido: int, total: Any) -> Any:
    row = db.execute(
        text("""
            SELECT COALESCE(SUM(valor), 0) AS pagado
            FROM ventas.pagos
            WHERE id_pedido = :id_pedido
              AND estado = 'aprobado'
        """),
        {"id_pedido": id_pedido},
    ).mappings().one()
    return max(total - row["pagado"], 0)


def mark_order_completed(db: Session, order: dict[str, Any]) -> None:
    table = ORDER_FRAGMENT_BY_SITE[order["id_sede"]]
    db.execute(
        text(f"""
            UPDATE {table}
            SET estado = 'completado'
            WHERE id_pedido = :id_pedido
              AND estado = 'pendiente'
        """),
        {"id_pedido": order["id_pedido"]},
    )


def create_payment(
    db: Session,
    *,
    id_pedido: int,
    valor: Any,
    medio_pago: str,
) -> dict[str, Any]:
    row = db.execute(
        text("""
            INSERT INTO ventas.pagos (id_pedido, valor, medio_pago, estado)
            VALUES (:id_pedido, :valor, :medio_pago, 'aprobado')
            RETURNING id_pago, id_pedido, fecha_pago, valor, medio_pago, estado
        """),
        {"id_pedido": id_pedido, "valor": valor, "medio_pago": medio_pago},
    ).mappings().one()
    return dict(row)


def list_payments(db: Session, id_pedido: int) -> list[dict[str, Any]]:
    rows = db.execute(
        text("""
            SELECT id_pago, id_pedido, fecha_pago, valor, medio_pago, estado
            FROM ventas.pagos
            WHERE id_pedido = :id_pedido
            ORDER BY fecha_pago DESC, id_pago DESC
        """),
        {"id_pedido": id_pedido},
    ).mappings().all()
    return [dict(row) for row in rows]


def create_return(
    db: Session,
    *,
    id_pedido: int,
    motivo: str,
    products: list[dict[str, Any]],
) -> dict[str, Any]:
    returned = db.execute(
        text("""
            SELECT dd.id_producto, COALESCE(SUM(dd.cantidad), 0) AS cantidad
            FROM ventas.devoluciones AS d
            JOIN ventas.detalle_devolucion AS dd
              ON dd.id_devolucion = d.id_devolucion
            WHERE d.id_pedido = :id_pedido
              AND d.estado IN ('pendiente', 'aprobada')
            GROUP BY dd.id_producto
        """),
        {"id_pedido": id_pedido},
    ).mappings().all()
    returned_by_product = {row["id_producto"]: row["cantidad"] for row in returned}
    sold_by_product = {
        row["id_producto"]: row["cantidad"]
        for row in list_order_details(db, id_pedido)
    }
    for product in products:
        id_producto = product["id_producto"]
        if id_producto not in sold_by_product:
            raise ValueError("El producto no pertenece al pedido")
        if (
            product["cantidad"]
            + returned_by_product.get(id_producto, 0)
            > sold_by_product[id_producto]
        ):
            raise ValueError("La cantidad solicitada supera la cantidad vendida pendiente de devolución")

    return_row = db.execute(
        text("""
            INSERT INTO ventas.devoluciones (id_pedido, motivo, estado)
            VALUES (:id_pedido, :motivo, 'pendiente')
            RETURNING id_devolucion, id_pedido, fecha_solicitud, motivo, estado
        """),
        {"id_pedido": id_pedido, "motivo": motivo},
    ).mappings().one()
    for product in products:
        db.execute(
            text("""
                INSERT INTO ventas.detalle_devolucion
                    (id_devolucion, id_producto, cantidad, condicion_producto)
                VALUES
                    (:id_devolucion, :id_producto, :cantidad, :condicion_producto)
            """),
            {"id_devolucion": return_row["id_devolucion"], **product},
        )
    return dict(return_row)


def list_returns(db: Session, id_pedido: int) -> list[dict[str, Any]]:
    rows = db.execute(
        text("""
            SELECT id_devolucion, id_pedido, fecha_solicitud, motivo, estado
            FROM ventas.devoluciones
            WHERE id_pedido = :id_pedido
            ORDER BY fecha_solicitud DESC, id_devolucion DESC
        """),
        {"id_pedido": id_pedido},
    ).mappings().all()
    return [dict(row) for row in rows]


def get_return(db: Session, id_devolucion: int) -> dict[str, Any] | None:
    row = db.execute(
        text("""
            SELECT id_devolucion, id_pedido, fecha_solicitud, motivo, estado
            FROM ventas.devoluciones
            WHERE id_devolucion = :id_devolucion
        """),
        {"id_devolucion": id_devolucion},
    ).mappings().first()
    return dict(row) if row is not None else None


def resolve_return(
    db: Session,
    *,
    id_devolucion: int,
    approve: bool,
) -> dict[str, Any] | None:
    candidate = get_return(db, id_devolucion)
    if candidate is None:
        return None
    order = lock_order(db, candidate["id_pedido"])
    if order is None:
        return None
    row = db.execute(
        text("""
            SELECT id_devolucion, id_pedido, estado
            FROM ventas.devoluciones
            WHERE id_devolucion = :id_devolucion
            FOR UPDATE
        """),
        {"id_devolucion": id_devolucion},
    ).mappings().first()
    if row is None:
        return None
    if row["estado"] != "pendiente":
        raise ValueError("Solo se pueden resolver devoluciones pendientes")
    if approve and order["estado"] not in ("completado", "devolucion"):
        raise ValueError("El pedido no admite la aprobación de devoluciones")
    state = "aprobada" if approve else "rechazada"
    resolved = db.execute(
        text("""
            UPDATE ventas.devoluciones
            SET estado = :estado
            WHERE id_devolucion = :id_devolucion
            RETURNING id_devolucion, id_pedido, fecha_solicitud, motivo, estado
        """),
        {"id_devolucion": id_devolucion, "estado": state},
    ).mappings().one()
    if approve:
        table = ORDER_FRAGMENT_BY_SITE[order["id_sede"]]
        db.execute(
            text(f"""
                UPDATE {table}
                SET estado = 'devolucion'
                WHERE id_pedido = :id_pedido
            """),
            {"id_pedido": order["id_pedido"]},
        )
    return dict(resolved)


def list_return_details(db: Session, id_devolucion: int) -> list[dict[str, Any]]:
    rows = db.execute(
        text("""
            SELECT id_devolucion, id_producto, cantidad, condicion_producto
            FROM ventas.detalle_devolucion
            WHERE id_devolucion = :id_devolucion
            ORDER BY id_producto
        """),
        {"id_devolucion": id_devolucion},
    ).mappings().all()
    return [dict(row) for row in rows]
