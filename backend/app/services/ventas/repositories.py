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
