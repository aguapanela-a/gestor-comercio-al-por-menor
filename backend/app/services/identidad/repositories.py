from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Integer, bindparam, text
from sqlalchemy.orm import Session


EMPLOYEE_COLUMNS = {
    "id_sede",
    "num_documento",
    "nombre_completo",
    "cargo",
    "correo",
    "estado",
}


def _utc_naive(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def list_employees(
    db: Session,
    *,
    id_sede: int | None,
    num_documento: str | None,
    estado: str | None,
    search: str | None,
    limit: int,
    offset: int,
) -> list[dict[str, Any]]:
    conditions: list[str] = []
    parameters: dict[str, Any] = {"limit": limit, "offset": offset}
    for column, value in (
        ("id_sede", id_sede),
        ("num_documento", num_documento),
        ("estado", estado),
    ):
        if value is not None:
            conditions.append(f"{column} = :{column}")
            parameters[column] = value
    if search is not None:
        conditions.append("nombre_completo ILIKE :search")
        parameters["search"] = f"%{search}%"
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    rows = db.execute(
        text(f"""
            SELECT id_empleado, id_sede, num_documento, nombre_completo,
                   cargo, correo, estado
            FROM identidad.empleados
            {where_clause}
            ORDER BY id_empleado
            LIMIT :limit OFFSET :offset
        """),
        parameters,
    ).mappings().all()
    return [dict(row) for row in rows]


def get_employee(db: Session, id_empleado: int) -> dict[str, Any] | None:
    row = db.execute(
        text("""
            SELECT id_empleado, id_sede, num_documento, nombre_completo,
                   cargo, correo, estado
            FROM identidad.empleados
            WHERE id_empleado = :id_empleado
        """),
        {"id_empleado": id_empleado},
    ).mappings().first()
    return dict(row) if row is not None else None


def create_employee(db: Session, values: dict[str, Any]) -> dict[str, Any]:
    row = db.execute(
        text("""
            INSERT INTO identidad.empleados
                (id_sede, num_documento, nombre_completo, cargo, correo, estado)
            VALUES
                (:id_sede, :num_documento, :nombre_completo, :cargo, :correo, :estado)
            RETURNING id_empleado, id_sede, num_documento, nombre_completo,
                      cargo, correo, estado
        """),
        values,
    ).mappings().one()
    return dict(row)


def update_employee(
    db: Session,
    id_empleado: int,
    values: dict[str, Any],
) -> dict[str, Any] | None:
    if not values:
        return get_employee(db, id_empleado)
    if not values.keys() <= EMPLOYEE_COLUMNS:
        raise ValueError("Invalid employee fields")
    assignments = ", ".join(f"{key} = :{key}" for key in values)
    parameters = {**values, "id_empleado": id_empleado}
    row = db.execute(
        text(f"""
            UPDATE identidad.empleados
            SET {assignments}
            WHERE id_empleado = :id_empleado
            RETURNING id_empleado, id_sede, num_documento, nombre_completo,
                      cargo, correo, estado
        """),
        parameters,
    ).mappings().first()
    return dict(row) if row is not None else None


def list_users(
    db: Session,
    *,
    id_empleado: int | None,
    estado: str | None,
    limit: int,
    offset: int,
) -> list[dict[str, Any]]:
    conditions: list[str] = []
    parameters: dict[str, Any] = {"limit": limit, "offset": offset}
    if id_empleado is not None:
        conditions.append("id_empleado = :id_empleado")
        parameters["id_empleado"] = id_empleado
    if estado is not None:
        conditions.append("estado = :estado")
        parameters["estado"] = estado
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    rows = db.execute(
        text(f"""
            SELECT id_usuario, id_empleado, nombre_usuario, estado, fecha_creacion
            FROM identidad.usuarios
            {where_clause}
            ORDER BY id_usuario
            LIMIT :limit OFFSET :offset
        """),
        parameters,
    ).mappings().all()
    return [dict(row) for row in rows]


def get_user(db: Session, id_usuario: int) -> dict[str, Any] | None:
    row = db.execute(
        text("""
            SELECT id_usuario, id_empleado, nombre_usuario, estado, fecha_creacion
            FROM identidad.usuarios
            WHERE id_usuario = :id_usuario
        """),
        {"id_usuario": id_usuario},
    ).mappings().first()
    return dict(row) if row is not None else None


def get_user_with_hash(db: Session, id_usuario: int) -> dict[str, Any] | None:
    row = db.execute(
        text("""
            SELECT id_usuario, id_empleado, nombre_usuario, password_hash, estado
            FROM identidad.usuarios
            WHERE id_usuario = :id_usuario
        """),
        {"id_usuario": id_usuario},
    ).mappings().first()
    return dict(row) if row is not None else None


def create_user(
    db: Session,
    *,
    id_empleado: int,
    nombre_usuario: str,
    password_hash: str,
) -> dict[str, Any]:
    row = db.execute(
        text("""
            INSERT INTO identidad.usuarios
                (id_empleado, nombre_usuario, password_hash, estado)
            VALUES
                (:id_empleado, :nombre_usuario, :password_hash, 'activo')
            RETURNING id_usuario, id_empleado, nombre_usuario, estado, fecha_creacion
        """),
        {
            "id_empleado": id_empleado,
            "nombre_usuario": nombre_usuario,
            "password_hash": password_hash,
        },
    ).mappings().one()
    return dict(row)


def update_user(
    db: Session,
    id_usuario: int,
    values: dict[str, Any],
) -> dict[str, Any] | None:
    allowed = {"nombre_usuario", "estado"}
    if not values:
        return get_user(db, id_usuario)
    if not values.keys() <= allowed:
        raise ValueError("Invalid user fields")
    assignments = ", ".join(f"{key} = :{key}" for key in values)
    row = db.execute(
        text(f"""
            UPDATE identidad.usuarios
            SET {assignments}
            WHERE id_usuario = :id_usuario
            RETURNING id_usuario, id_empleado, nombre_usuario, estado, fecha_creacion
        """),
        {**values, "id_usuario": id_usuario},
    ).mappings().first()
    return dict(row) if row is not None else None

def change_user_password(
    db: Session,
    id_usuario: int,
    password_hash: str,
) -> bool:
    result = db.execute(
        text("""
            UPDATE identidad.usuarios
            SET password_hash = :password_hash
            WHERE id_usuario = :id_usuario AND estado = 'activo'
        """),
        {"password_hash": password_hash, "id_usuario": id_usuario},
    )
    return result.rowcount == 1


def list_access_audit(
    db: Session,
    *,
    id_usuario: int,
    limit: int,
    offset: int,
    id_usuario_filtro: int | None = None,
    microservicio: str | None = None,
    modulo: str | None = None,
    accion: str | None = None,
    resultado: str | None = None,
    fecha_desde: datetime | None = None,
    fecha_hasta: datetime | None = None,
    texto: str | None = None,
) -> list[dict[str, Any]]:
    query = text("""
            WITH global_audit_access AS (
                SELECT EXISTS (
                    SELECT 1
                    FROM identidad.usuarios_roles AS user_role
                    JOIN identidad.roles_aplicacion AS app_role
                      ON app_role.id_rol = user_role.id_rol
                    WHERE user_role.id_usuario = :id_usuario
                      AND app_role.codigo IN (
                          :auditor_role,
                          :administrator_role
                      )
                ) AS allowed
            )
            SELECT audit.id_auditoria,
                   audit.id_usuario,
                   audit.fecha_hora,
                   audit.accion,
                   audit.objeto_consultado,
                   audit.event_id,
                   audit.microservicio,
                   audit.modulo,
                   audit.tipo_objeto,
                   audit.id_objeto,
                   audit.resultado,
                   audit.metodo_http,
                   audit.ruta,
                   audit.direccion_ip,
                   audit.correlation_id,
                   audit.detalles,
                   users.nombre_usuario,
                   employees.nombre_completo
            FROM identidad.auditoria_accesos AS audit
            CROSS JOIN global_audit_access AS access
            LEFT JOIN identidad.usuarios AS users
              ON users.id_usuario = audit.id_usuario
            LEFT JOIN identidad.empleados AS employees
              ON employees.id_empleado = users.id_empleado
            WHERE (
                    (access.allowed AND
                     (CAST(:id_usuario_filtro AS INTEGER) IS NULL OR audit.id_usuario = CAST(:id_usuario_filtro AS INTEGER)))
                    OR
                    (NOT access.allowed AND audit.id_usuario = :id_usuario)
                  )
              AND (CAST(:microservicio AS TEXT) IS NULL OR audit.microservicio = CAST(:microservicio AS TEXT))
              AND (CAST(:modulo AS TEXT) IS NULL OR audit.modulo = CAST(:modulo AS TEXT))
              AND (CAST(:accion AS TEXT) IS NULL OR LOWER(audit.accion) LIKE CAST(:accion AS TEXT))
              AND (CAST(:resultado AS TEXT) IS NULL OR audit.resultado = CAST(:resultado AS TEXT))
              AND (:fecha_desde IS NULL OR audit.fecha_hora >= :fecha_desde)
              AND (:fecha_hasta IS NULL OR audit.fecha_hora <= :fecha_hasta)
              AND (
                    CAST(:texto AS TEXT) IS NULL
                    OR LOWER(COALESCE(audit.objeto_consultado, '')) LIKE CAST(:texto AS TEXT)
                    OR LOWER(COALESCE(audit.tipo_objeto, '')) LIKE CAST(:texto AS TEXT)
                    OR LOWER(COALESCE(audit.id_objeto, '')) LIKE CAST(:texto AS TEXT)
                    OR LOWER(COALESCE(audit.ruta, '')) LIKE CAST(:texto AS TEXT)
                    OR LOWER(COALESCE(audit.accion, '')) LIKE CAST(:texto AS TEXT)
                  )
            ORDER BY audit.fecha_hora DESC, audit.id_auditoria DESC
            LIMIT :limit OFFSET :offset
        """).bindparams(
        bindparam("fecha_desde", type_=DateTime()),
        bindparam("fecha_hasta", type_=DateTime()),
    )
    rows = db.execute(
        query,
        {
            "id_usuario": id_usuario,
            "auditor_role": "auditor",
            "administrator_role": "administrador",
            "id_usuario_filtro": id_usuario_filtro,
            "microservicio": microservicio,
            "modulo": modulo,
            "accion": f"%{accion.lower()}%" if accion else None,
            "resultado": resultado,
            "fecha_desde": _utc_naive(fecha_desde),
            "fecha_hasta": _utc_naive(fecha_hasta),
            "texto": f"%{texto.lower()}%" if texto else None,
            "limit": limit,
            "offset": offset,
        },
    ).mappings().all()
    return [dict(row) for row in rows]


def get_user_profile(db: Session, id_usuario: int) -> dict[str, Any] | None:
    row = db.execute(
        text("""
            SELECT u.id_usuario, u.id_empleado, u.nombre_usuario,
                   u.estado AS estado_usuario,
                   e.nombre_completo, e.cargo, e.id_sede, e.correo,
                   e.estado AS estado_empleado
            FROM identidad.usuarios AS u
            JOIN identidad.empleados AS e
              ON e.id_empleado = u.id_empleado
            WHERE u.id_usuario = :id_usuario
        """),
        {"id_usuario": id_usuario},
    ).mappings().first()
    return dict(row) if row is not None else None
