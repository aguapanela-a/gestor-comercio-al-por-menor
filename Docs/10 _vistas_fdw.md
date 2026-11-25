# Vistas de reportes con `postgres_fdw`

Este documento presenta las 10 vistas obligatorias de la capa `reportes`, construidas sobre los 6 microservicios mediante la extensión `postgres_fdw`. Están divididas en **dos bloques de 5 vistas**; cada bloque es autónomo: habilita la extensión, registra únicamente los servidores remotos que necesita, mapea los usuarios, crea las tablas foráneas y, al final, crea y deja listas sus 5 vistas.

## ¿Cómo funciona `postgres_fdw` desde `reportes`?

Las bases de datos de los microservicios están en servidores distintos, así que `reportes` no puede hacer un `JOIN` directo entre ellas. `postgres_fdw` (*foreign data wrapper*) resuelve esto: la base de `reportes` consulta las tablas remotas como si fueran locales y PostgreSQL envía las consultas necesarias a cada servidor. Cada pieza cumple un papel:

- **`CREATE EXTENSION postgres_fdw`**: instala en la base de `reportes` el conector que sabe hablar con otros servidores PostgreSQL.
- **`CREATE SERVER`**: registra un servidor remoto (host, puerto y nombre de la base de datos). Se crea uno por microservicio que la vista necesite.
- **`CREATE USER MAPPING`**: indica con qué credenciales se conecta el usuario local (`CURRENT_USER`) a cada servidor remoto. Se usa `user_pg_fdw`, el usuario de integración de cada microservicio, que tiene permiso de `CONNECT`, `USAGE` sobre el esquema y `SELECT, UPDATE` sobre sus tablas.
- **`CREATE FOREIGN TABLE`**: define en `reportes` una tabla "espejo" que apunta a una tabla real del servidor remoto (`schema_name` y `table_name`). No guarda datos: cada consulta lee los datos remotos en el momento. Se crean en esquemas locales `ext_<microservicio>` para mantener ordenada la capa de reportes.
- **`CREATE VIEW`**: las vistas del esquema `reportes` combinan las tablas foráneas con `JOIN`, CTE y funciones de agregación. Como no guardan datos, siempre muestran el estado actual de los microservicios y solo leen: ninguna vista modifica datos operativos.

Las tablas `inventarios` y `pedidos_venta` están particionadas por `id_sede` en sus servidores. Para `postgres_fdw` son una sola tabla (la tabla madre), por lo que cada una se apunta con una única tabla foránea y no hace falta unir los fragmentos con `UNION ALL`.

## Distribución de las vistas en los dos bloques

| Bloque | Vistas | Servidores remotos usados |
|---|---|---|
| **Bloque 1** | 1. `vista_inventario_por_sede`<br>2. `vista_alertas_reabastecimiento`<br>3. `vista_productos_sin_inventario`<br>7. `vista_compras_pendientes`<br>8. `vista_transferencias_en_transito` | `catalogo`, `compras`, `inventarios`, `organizacion` (4 servidores) |
| **Bloque 2** | 4. `vista_ventas_mensuales_por_sede`<br>5. `vista_pedidos_pendientes`<br>6. `vista_saldos_pendientes`<br>9. `vista_devoluciones_por_producto`<br>10. `vista_reporte_corporativo` | `catalogo`, `compras`, `identidad`, `inventarios`, `organizacion`, `ventas` (los 6 servidores) |

La vista 2 depende de la vista 1, por eso van en el mismo bloque. Los dos bloques usan los mismos nombres de servidor, mapeos y tablas foráneas, así que pueden ejecutarse en la misma base de datos sin conflictos.

## Bloque 1: vistas 1, 2, 3, 7 y 8

```sql
-- Extensión
CREATE EXTENSION IF NOT EXISTS postgres_fdw;

-- Servidores remotos
CREATE SERVER IF NOT EXISTS catalogo_server
    FOREIGN DATA WRAPPER postgres_fdw
    OPTIONS (
        host 'catalogo-db-server.postgres.database.azure.com',
        port '5432',
        dbname 'catalogo_db'
    );

CREATE SERVER IF NOT EXISTS compras_server
    FOREIGN DATA WRAPPER postgres_fdw
    OPTIONS (
        host 'compras-db-server.postgres.database.azure.com',
        port '5432',
        dbname 'compras_db'
    );

CREATE SERVER IF NOT EXISTS inventarios_server
    FOREIGN DATA WRAPPER postgres_fdw
    OPTIONS (
        host 'inventarios-db-server.postgres.database.azure.com',
        port '5432',
        dbname 'inventarios_db'
    );

CREATE SERVER IF NOT EXISTS organizacion_server
    FOREIGN DATA WRAPPER postgres_fdw
    OPTIONS (
        host 'organizacion-db-server.postgres.database.azure.com',
        port '5432',
        dbname 'organizacion_db'
    );

-- Mapeo de usuarios (user_pg_fdw de cada microservicio)
CREATE USER MAPPING IF NOT EXISTS FOR CURRENT_USER
    SERVER catalogo_server
    OPTIONS (
        user 'user_pg_fdw',
        password 'Ctl_Fdw#2026!mR4'
    );

CREATE USER MAPPING IF NOT EXISTS FOR CURRENT_USER
    SERVER compras_server
    OPTIONS (
        user 'user_pg_fdw',
        password 'Cmp_Fdw#2026!pV8'
    );

CREATE USER MAPPING IF NOT EXISTS FOR CURRENT_USER
    SERVER inventarios_server
    OPTIONS (
        user 'user_pg_fdw',
        password 'Inv_Fdw#2026!qY6'
    );

CREATE USER MAPPING IF NOT EXISTS FOR CURRENT_USER
    SERVER organizacion_server
    OPTIONS (
        user 'user_pg_fdw',
        password 'Org_Fdw#2026!nS2'
    );

-- Esquemas locales: uno por servidor remoto para las tablas foráneas, y reportes para las vistas
CREATE SCHEMA IF NOT EXISTS ext_catalogo;
CREATE SCHEMA IF NOT EXISTS ext_compras;
CREATE SCHEMA IF NOT EXISTS ext_inventarios;
CREATE SCHEMA IF NOT EXISTS ext_organizacion;
CREATE SCHEMA IF NOT EXISTS reportes;

-- Tablas foráneas
CREATE FOREIGN TABLE IF NOT EXISTS ext_catalogo.categorias (
    id_categoria  INTEGER,
    nombre        VARCHAR(80)
)
SERVER catalogo_server
OPTIONS (schema_name 'catalogo', table_name 'categorias');

CREATE FOREIGN TABLE IF NOT EXISTS ext_catalogo.productos (
    id_producto   INTEGER,
    sku           VARCHAR(30),
    nombre        VARCHAR(120),
    id_categoria  INTEGER,
    precio_lista  NUMERIC(12,2),
    estado        VARCHAR(10)
)
SERVER catalogo_server
OPTIONS (schema_name 'catalogo', table_name 'productos');

CREATE FOREIGN TABLE IF NOT EXISTS ext_compras.proveedores (
    id_proveedor  INTEGER,
    razon_social  VARCHAR(100)
)
SERVER compras_server
OPTIONS (schema_name 'compras', table_name 'proveedores');

CREATE FOREIGN TABLE IF NOT EXISTS ext_compras.ordenes_compra (
    id_orden_compra     INTEGER,
    id_proveedor        INTEGER,
    id_almacen_destino  INTEGER,
    fecha_orden         TIMESTAMP,
    fecha_estimada      DATE,
    estado              VARCHAR(20)
)
SERVER compras_server
OPTIONS (schema_name 'compras', table_name 'ordenes_compra');

CREATE FOREIGN TABLE IF NOT EXISTS ext_compras.detalle_orden_compra (
    id_orden_compra      INTEGER,
    id_producto          INTEGER,
    cantidad_solicitada  INTEGER,
    costo_unitario       NUMERIC(12,2)
)
SERVER compras_server
OPTIONS (schema_name 'compras', table_name 'detalle_orden_compra');

CREATE FOREIGN TABLE IF NOT EXISTS ext_compras.recepciones_compra (
    id_recepcion     INTEGER,
    id_orden_compra  INTEGER,
    estado           VARCHAR(20)
)
SERVER compras_server
OPTIONS (schema_name 'compras', table_name 'recepciones_compra');

CREATE FOREIGN TABLE IF NOT EXISTS ext_compras.detalle_recepcion (
    id_recepcion       INTEGER,
    id_producto        INTEGER,
    cantidad_recibida  INTEGER
)
SERVER compras_server
OPTIONS (schema_name 'compras', table_name 'detalle_recepcion');

CREATE FOREIGN TABLE IF NOT EXISTS ext_inventarios.inventarios (
    id_sede            INTEGER,
    id_almacen         INTEGER,
    id_producto        INTEGER,
    existencia_actual  INTEGER,
    stock_minimo       INTEGER
)
SERVER inventarios_server
OPTIONS (schema_name 'inventarios', table_name 'inventarios');

CREATE FOREIGN TABLE IF NOT EXISTS ext_inventarios.transferencias (
    id_transferencia    INTEGER,
    id_almacen_origen   INTEGER,
    id_almacen_destino  INTEGER,
    fecha_despacho      TIMESTAMP,
    fecha_recepcion     TIMESTAMP,
    estado              VARCHAR(20)
)
SERVER inventarios_server
OPTIONS (schema_name 'inventarios', table_name 'transferencias');

CREATE FOREIGN TABLE IF NOT EXISTS ext_inventarios.detalle_transferencia (
    id_transferencia  INTEGER,
    id_producto       INTEGER,
    cantidad_enviada  INTEGER
)
SERVER inventarios_server
OPTIONS (schema_name 'inventarios', table_name 'detalle_transferencia');

CREATE FOREIGN TABLE IF NOT EXISTS ext_organizacion.sedes (
    id_sede    INTEGER,
    nombre     VARCHAR(80),
    tipo_sede  VARCHAR(15),
    estado     VARCHAR(10)
)
SERVER organizacion_server
OPTIONS (schema_name 'organizacion', table_name 'sedes');

CREATE FOREIGN TABLE IF NOT EXISTS ext_organizacion.almacenes (
    id_almacen  INTEGER,
    id_sede     INTEGER,
    nombre      VARCHAR(80)
)
SERVER organizacion_server
OPTIONS (schema_name 'organizacion', table_name 'almacenes');

-- Vistas
-- 1) vista_inventario_por_sede
CREATE OR REPLACE VIEW reportes.vista_inventario_por_sede AS
SELECT i.id_sede, s.nombre AS sede, i.id_almacen, a.nombre AS almacen,
       p.id_producto, p.sku, p.nombre AS producto, c.nombre AS categoria,
       i.existencia_actual, i.stock_minimo, p.precio_lista,
       i.existencia_actual * p.precio_lista AS valorizacion_estimada
FROM ext_inventarios.inventarios i
JOIN ext_catalogo.productos     p ON p.id_producto  = i.id_producto
JOIN ext_catalogo.categorias    c ON c.id_categoria = p.id_categoria
JOIN ext_organizacion.almacenes a ON a.id_almacen   = i.id_almacen
JOIN ext_organizacion.sedes     s ON s.id_sede      = i.id_sede;

-- 2) vista_alertas_reabastecimiento
CREATE OR REPLACE VIEW reportes.vista_alertas_reabastecimiento AS
SELECT v.id_sede, v.sede, v.id_almacen, v.almacen, v.id_producto, v.sku, v.producto,
       v.existencia_actual, v.stock_minimo,
       v.stock_minimo - v.existencia_actual AS faltante,
       CASE WHEN v.existencia_actual = 0 THEN 'SIN EXISTENCIA' ELSE 'BAJO EL MINIMO' END AS nivel_alerta
FROM reportes.vista_inventario_por_sede v
WHERE v.existencia_actual = 0 OR v.existencia_actual < v.stock_minimo
ORDER BY faltante DESC, v.sede, v.producto;

-- 3) vista_productos_sin_inventario
CREATE OR REPLACE VIEW reportes.vista_productos_sin_inventario AS
SELECT s.id_sede, s.nombre AS sede, p.id_producto, p.sku, p.nombre AS producto
FROM ext_catalogo.productos p
CROSS JOIN ext_organizacion.sedes s
WHERE p.estado = 'activo' AND s.estado = 'activo'
  AND NOT EXISTS (SELECT 1 FROM ext_inventarios.inventarios i
                  WHERE i.id_producto = p.id_producto AND i.id_sede = s.id_sede);

-- 7) vista_compras_pendientes
CREATE OR REPLACE VIEW reportes.vista_compras_pendientes AS
WITH recibido AS (
  SELECT r.id_orden_compra, dr.id_producto, sum(dr.cantidad_recibida) AS cantidad_recibida
  FROM ext_compras.recepciones_compra r
  JOIN ext_compras.detalle_recepcion dr ON dr.id_recepcion = r.id_recepcion
  WHERE r.estado = 'procesada'
  GROUP BY r.id_orden_compra, dr.id_producto
)
SELECT oc.id_orden_compra, pr.razon_social AS proveedor, oc.id_almacen_destino, a.nombre AS almacen_destino,
       oc.fecha_orden, oc.fecha_estimada, oc.estado AS estado_orden,
       d.id_producto, p.nombre AS producto, d.cantidad_solicitada,
       COALESCE(rc.cantidad_recibida, 0) AS cantidad_recibida,
       d.cantidad_solicitada - COALESCE(rc.cantidad_recibida, 0) AS cantidad_pendiente
FROM ext_compras.ordenes_compra oc
JOIN ext_compras.detalle_orden_compra d ON d.id_orden_compra = oc.id_orden_compra
JOIN ext_compras.proveedores pr         ON pr.id_proveedor   = oc.id_proveedor
JOIN ext_catalogo.productos p           ON p.id_producto     = d.id_producto
JOIN ext_organizacion.almacenes a       ON a.id_almacen      = oc.id_almacen_destino
LEFT JOIN recibido rc ON rc.id_orden_compra = d.id_orden_compra AND rc.id_producto = d.id_producto
WHERE oc.estado <> 'cancelada'
  AND d.cantidad_solicitada > COALESCE(rc.cantidad_recibida, 0);

-- 8) vista_transferencias_en_transito
CREATE OR REPLACE VIEW reportes.vista_transferencias_en_transito AS
SELECT t.id_transferencia, t.id_almacen_origen, ao.nombre AS almacen_origen, so.nombre AS sede_origen,
       t.id_almacen_destino, ad.nombre AS almacen_destino, sd.nombre AS sede_destino,
       t.fecha_despacho, CURRENT_DATE - t.fecha_despacho::date AS dias_transcurridos,
       d.id_producto, p.nombre AS producto, d.cantidad_enviada
FROM ext_inventarios.transferencias t
JOIN ext_inventarios.detalle_transferencia d ON d.id_transferencia = t.id_transferencia
JOIN ext_catalogo.productos p                ON p.id_producto = d.id_producto
JOIN ext_organizacion.almacenes ao ON ao.id_almacen = t.id_almacen_origen
JOIN ext_organizacion.sedes     so ON so.id_sede    = ao.id_sede
JOIN ext_organizacion.almacenes ad ON ad.id_almacen = t.id_almacen_destino
JOIN ext_organizacion.sedes     sd ON sd.id_sede    = ad.id_sede
WHERE t.fecha_despacho IS NOT NULL AND t.fecha_recepcion IS NULL AND t.estado <> 'cancelada';
```

## Bloque 2: vistas 4, 5, 6, 9 y 10

```sql
-- Extensión
CREATE EXTENSION IF NOT EXISTS postgres_fdw;

-- Servidores remotos
CREATE SERVER IF NOT EXISTS catalogo_server
    FOREIGN DATA WRAPPER postgres_fdw
    OPTIONS (
        host 'catalogo-db-server.postgres.database.azure.com',
        port '5432',
        dbname 'catalogo_db'
    );

CREATE SERVER IF NOT EXISTS compras_server
    FOREIGN DATA WRAPPER postgres_fdw
    OPTIONS (
        host 'compras-db-server.postgres.database.azure.com',
        port '5432',
        dbname 'compras_db'
    );

CREATE SERVER IF NOT EXISTS identidad_server
    FOREIGN DATA WRAPPER postgres_fdw
    OPTIONS (
        host 'identidad-db-server.postgres.database.azure.com',
        port '5432',
        dbname 'identidad_db'
    );

CREATE SERVER IF NOT EXISTS inventarios_server
    FOREIGN DATA WRAPPER postgres_fdw
    OPTIONS (
        host 'inventarios-db-server.postgres.database.azure.com',
        port '5432',
        dbname 'inventarios_db'
    );

CREATE SERVER IF NOT EXISTS organizacion_server
    FOREIGN DATA WRAPPER postgres_fdw
    OPTIONS (
        host 'organizacion-db-server.postgres.database.azure.com',
        port '5432',
        dbname 'organizacion_db'
    );

CREATE SERVER IF NOT EXISTS ventas_server
    FOREIGN DATA WRAPPER postgres_fdw
    OPTIONS (
        host 'ventas-db-server.postgres.database.azure.com',
        port '5432',
        dbname 'ventas_db'
    );

-- Mapeo de usuarios (user_pg_fdw de cada microservicio)
CREATE USER MAPPING IF NOT EXISTS FOR CURRENT_USER
    SERVER catalogo_server
    OPTIONS (
        user 'user_pg_fdw',
        password 'Ctl_Fdw#2026!mR4'
    );

CREATE USER MAPPING IF NOT EXISTS FOR CURRENT_USER
    SERVER compras_server
    OPTIONS (
        user 'user_pg_fdw',
        password 'Cmp_Fdw#2026!pV8'
    );

CREATE USER MAPPING IF NOT EXISTS FOR CURRENT_USER
    SERVER identidad_server
    OPTIONS (
        user 'user_pg_fdw',
        password 'Idn_Fdw#2026!sJ3'
    );

CREATE USER MAPPING IF NOT EXISTS FOR CURRENT_USER
    SERVER inventarios_server
    OPTIONS (
        user 'user_pg_fdw',
        password 'Inv_Fdw#2026!qY6'
    );

CREATE USER MAPPING IF NOT EXISTS FOR CURRENT_USER
    SERVER organizacion_server
    OPTIONS (
        user 'user_pg_fdw',
        password 'Org_Fdw#2026!nS2'
    );

CREATE USER MAPPING IF NOT EXISTS FOR CURRENT_USER
    SERVER ventas_server
    OPTIONS (
        user 'user_pg_fdw',
        password 'Vta_Fdw#2026!rU4'
    );

-- Esquemas locales: uno por servidor remoto para las tablas foráneas, y reportes para las vistas
CREATE SCHEMA IF NOT EXISTS ext_catalogo;
CREATE SCHEMA IF NOT EXISTS ext_compras;
CREATE SCHEMA IF NOT EXISTS ext_identidad;
CREATE SCHEMA IF NOT EXISTS ext_inventarios;
CREATE SCHEMA IF NOT EXISTS ext_organizacion;
CREATE SCHEMA IF NOT EXISTS ext_ventas;
CREATE SCHEMA IF NOT EXISTS reportes;

-- Tablas foráneas
CREATE FOREIGN TABLE IF NOT EXISTS ext_catalogo.categorias (
    id_categoria  INTEGER,
    nombre        VARCHAR(80)
)
SERVER catalogo_server
OPTIONS (schema_name 'catalogo', table_name 'categorias');

CREATE FOREIGN TABLE IF NOT EXISTS ext_catalogo.productos (
    id_producto   INTEGER,
    sku           VARCHAR(30),
    nombre        VARCHAR(120),
    id_categoria  INTEGER,
    precio_lista  NUMERIC(12,2),
    estado        VARCHAR(10)
)
SERVER catalogo_server
OPTIONS (schema_name 'catalogo', table_name 'productos');

CREATE FOREIGN TABLE IF NOT EXISTS ext_compras.ordenes_compra (
    id_orden_compra     INTEGER,
    id_proveedor        INTEGER,
    id_almacen_destino  INTEGER,
    fecha_orden         TIMESTAMP,
    fecha_estimada      DATE,
    estado              VARCHAR(20)
)
SERVER compras_server
OPTIONS (schema_name 'compras', table_name 'ordenes_compra');

CREATE FOREIGN TABLE IF NOT EXISTS ext_compras.detalle_orden_compra (
    id_orden_compra      INTEGER,
    id_producto          INTEGER,
    cantidad_solicitada  INTEGER,
    costo_unitario       NUMERIC(12,2)
)
SERVER compras_server
OPTIONS (schema_name 'compras', table_name 'detalle_orden_compra');

CREATE FOREIGN TABLE IF NOT EXISTS ext_identidad.empleados (
    id_empleado      INTEGER,
    nombre_completo  VARCHAR(120)
)
SERVER identidad_server
OPTIONS (schema_name 'identidad', table_name 'empleados');

CREATE FOREIGN TABLE IF NOT EXISTS ext_inventarios.inventarios (
    id_sede            INTEGER,
    id_almacen         INTEGER,
    id_producto        INTEGER,
    existencia_actual  INTEGER,
    stock_minimo       INTEGER
)
SERVER inventarios_server
OPTIONS (schema_name 'inventarios', table_name 'inventarios');

CREATE FOREIGN TABLE IF NOT EXISTS ext_inventarios.transferencias (
    id_transferencia    INTEGER,
    id_almacen_origen   INTEGER,
    id_almacen_destino  INTEGER,
    fecha_despacho      TIMESTAMP,
    fecha_recepcion     TIMESTAMP,
    estado              VARCHAR(20)
)
SERVER inventarios_server
OPTIONS (schema_name 'inventarios', table_name 'transferencias');

CREATE FOREIGN TABLE IF NOT EXISTS ext_organizacion.sedes (
    id_sede    INTEGER,
    nombre     VARCHAR(80),
    tipo_sede  VARCHAR(15),
    estado     VARCHAR(10)
)
SERVER organizacion_server
OPTIONS (schema_name 'organizacion', table_name 'sedes');

CREATE FOREIGN TABLE IF NOT EXISTS ext_organizacion.almacenes (
    id_almacen  INTEGER,
    id_sede     INTEGER,
    nombre      VARCHAR(80)
)
SERVER organizacion_server
OPTIONS (schema_name 'organizacion', table_name 'almacenes');

CREATE FOREIGN TABLE IF NOT EXISTS ext_ventas.clientes (
    id_cliente       INTEGER,
    nombre_completo  VARCHAR(120)
)
SERVER ventas_server
OPTIONS (schema_name 'ventas', table_name 'clientes');

CREATE FOREIGN TABLE IF NOT EXISTS ext_ventas.pedidos_venta (
    id_pedido         INTEGER,
    id_sede           INTEGER,
    id_almacen        INTEGER,
    id_cliente        INTEGER,
    id_empleado       INTEGER,
    fecha_pedido      DATE,
    estado            VARCHAR(15),
    total_registrado  NUMERIC(14,2)
)
SERVER ventas_server
OPTIONS (schema_name 'ventas', table_name 'pedidos_venta');

CREATE FOREIGN TABLE IF NOT EXISTS ext_ventas.detalle_pedido (
    id_pedido    INTEGER,
    id_sede      INTEGER,
    id_producto  INTEGER,
    cantidad     INTEGER
)
SERVER ventas_server
OPTIONS (schema_name 'ventas', table_name 'detalle_pedido');

CREATE FOREIGN TABLE IF NOT EXISTS ext_ventas.pagos (
    id_pedido  INTEGER,
    valor      NUMERIC(14,2),
    estado     VARCHAR(15)
)
SERVER ventas_server
OPTIONS (schema_name 'ventas', table_name 'pagos');

CREATE FOREIGN TABLE IF NOT EXISTS ext_ventas.devoluciones (
    id_devolucion  INTEGER,
    estado         VARCHAR(15)
)
SERVER ventas_server
OPTIONS (schema_name 'ventas', table_name 'devoluciones');

CREATE FOREIGN TABLE IF NOT EXISTS ext_ventas.detalle_devolucion (
    id_devolucion  INTEGER,
    id_producto    INTEGER,
    cantidad       INTEGER
)
SERVER ventas_server
OPTIONS (schema_name 'ventas', table_name 'detalle_devolucion');

-- Vistas
-- 4) vista_ventas_mensuales_por_sede
CREATE OR REPLACE VIEW reportes.vista_ventas_mensuales_por_sede AS
WITH mensual AS (
  SELECT p.id_sede, date_trunc('month', p.fecha_pedido)::date AS mes,
         count(*) AS pedidos, sum(p.total_registrado) AS total_vendido
  FROM ext_ventas.pedidos_venta p
  WHERE p.estado = 'completado'
  GROUP BY p.id_sede, date_trunc('month', p.fecha_pedido)
)
SELECT m.id_sede, s.nombre AS sede, m.mes, m.pedidos, m.total_vendido,
       LAG(m.total_vendido) OVER (PARTITION BY m.id_sede ORDER BY m.mes) AS total_mes_anterior,
       m.total_vendido - LAG(m.total_vendido) OVER (PARTITION BY m.id_sede ORDER BY m.mes) AS variacion,
       ROUND(100.0 * (m.total_vendido - LAG(m.total_vendido) OVER (PARTITION BY m.id_sede ORDER BY m.mes))
             / NULLIF(LAG(m.total_vendido) OVER (PARTITION BY m.id_sede ORDER BY m.mes), 0), 2) AS variacion_pct
FROM mensual m
JOIN ext_organizacion.sedes s ON s.id_sede = m.id_sede;

-- 5) vista_pedidos_pendientes
CREATE OR REPLACE VIEW reportes.vista_pedidos_pendientes AS
SELECT p.id_pedido, p.id_sede, s.nombre AS sede, p.id_almacen, a.nombre AS almacen,
       p.id_cliente, c.nombre_completo AS cliente, p.id_empleado, e.nombre_completo AS vendedor,
       p.fecha_pedido, CURRENT_DATE - p.fecha_pedido AS dias_antiguedad, p.total_registrado
FROM ext_ventas.pedidos_venta p
JOIN ext_organizacion.sedes     s ON s.id_sede    = p.id_sede
JOIN ext_organizacion.almacenes a ON a.id_almacen = p.id_almacen
JOIN ext_ventas.clientes        c ON c.id_cliente = p.id_cliente
LEFT JOIN ext_identidad.empleados e ON e.id_empleado = p.id_empleado
WHERE p.estado = 'pendiente';

-- 6) vista_saldos_pendientes
CREATE OR REPLACE VIEW reportes.vista_saldos_pendientes AS
WITH pagado AS (
  SELECT id_pedido, sum(valor) AS pagos_confirmados
  FROM ext_ventas.pagos WHERE estado = 'aprobado' GROUP BY id_pedido
)
SELECT p.id_pedido, p.id_sede, s.nombre AS sede, p.id_cliente, c.nombre_completo AS cliente,
       p.fecha_pedido, p.total_registrado,
       COALESCE(g.pagos_confirmados, 0) AS pagos_confirmados,
       p.total_registrado - COALESCE(g.pagos_confirmados, 0) AS saldo_pendiente
FROM ext_ventas.pedidos_venta p
JOIN ext_organizacion.sedes s ON s.id_sede = p.id_sede
JOIN ext_ventas.clientes    c ON c.id_cliente = p.id_cliente
LEFT JOIN pagado g ON g.id_pedido = p.id_pedido
WHERE p.estado <> 'cancelado'
  AND p.total_registrado - COALESCE(g.pagos_confirmados, 0) > 0;

-- 9) vista_devoluciones_por_producto
CREATE OR REPLACE VIEW reportes.vista_devoluciones_por_producto AS
WITH vendidas AS (
  SELECT d.id_producto, sum(d.cantidad) AS cantidad_vendida
  FROM ext_ventas.detalle_pedido d
  JOIN ext_ventas.pedidos_venta p ON p.id_pedido = d.id_pedido AND p.id_sede = d.id_sede
  WHERE p.estado IN ('completado', 'devolucion')
  GROUP BY d.id_producto
), devueltas AS (
  SELECT dd.id_producto, sum(dd.cantidad) AS cantidad_devuelta
  FROM ext_ventas.detalle_devolucion dd
  JOIN ext_ventas.devoluciones dv ON dv.id_devolucion = dd.id_devolucion
  WHERE dv.estado <> 'rechazada'
  GROUP BY dd.id_producto
)
SELECT p.id_producto, p.sku, p.nombre AS producto, c.nombre AS categoria,
       v.cantidad_vendida, COALESCE(dv.cantidad_devuelta, 0) AS cantidad_devuelta,
       ROUND(100.0 * COALESCE(dv.cantidad_devuelta, 0) / NULLIF(v.cantidad_vendida, 0), 2) AS porcentaje_devolucion
FROM vendidas v
JOIN ext_catalogo.productos  p ON p.id_producto  = v.id_producto
JOIN ext_catalogo.categorias c ON c.id_categoria = p.id_categoria
LEFT JOIN devueltas dv ON dv.id_producto = v.id_producto;

-- 10) vista_reporte_corporativo
CREATE OR REPLACE VIEW reportes.vista_reporte_corporativo AS
WITH inv AS (
  SELECT i.id_sede,
         count(DISTINCT i.id_producto) FILTER (WHERE p.estado = 'activo') AS productos_activos,
         sum(i.existencia_actual) AS unidades_inventario
  FROM ext_inventarios.inventarios i
  JOIN ext_catalogo.productos p ON p.id_producto = i.id_producto
  GROUP BY i.id_sede
), ped AS (
  SELECT id_sede,
         COALESCE(sum(total_registrado) FILTER (WHERE estado = 'completado'), 0) AS ventas_total,
         count(*) FILTER (WHERE estado = 'pendiente') AS pedidos_pendientes
  FROM ext_ventas.pedidos_venta
  GROUP BY id_sede
), compra_orden AS (
  SELECT oc.id_orden_compra, oc.id_almacen_destino,
         sum(d.cantidad_solicitada * d.costo_unitario) AS valor_orden
  FROM ext_compras.ordenes_compra oc
  JOIN ext_compras.detalle_orden_compra d ON d.id_orden_compra = oc.id_orden_compra
  WHERE oc.estado <> 'cancelada'
  GROUP BY oc.id_orden_compra, oc.id_almacen_destino
), com AS (
  SELECT a.id_sede, count(*) AS ordenes_compra, sum(co.valor_orden) AS valor_compras
  FROM compra_orden co
  JOIN ext_organizacion.almacenes a ON a.id_almacen = co.id_almacen_destino
  GROUP BY a.id_sede
), tr_env AS (
  SELECT ao.id_sede, count(*) AS transferencias_enviadas
  FROM ext_inventarios.transferencias t
  JOIN ext_organizacion.almacenes ao ON ao.id_almacen = t.id_almacen_origen
  GROUP BY ao.id_sede
), tr_rec AS (
  SELECT ad.id_sede, count(*) AS transferencias_recibidas
  FROM ext_inventarios.transferencias t
  JOIN ext_organizacion.almacenes ad ON ad.id_almacen = t.id_almacen_destino
  GROUP BY ad.id_sede
)
SELECT s.id_sede, s.nombre AS sede, s.tipo_sede,
       COALESCE(inv.productos_activos, 0)       AS productos_activos,
       COALESCE(inv.unidades_inventario, 0)     AS unidades_inventario,
       COALESCE(ped.ventas_total, 0)            AS ventas_total,
       COALESCE(ped.pedidos_pendientes, 0)      AS pedidos_pendientes,
       COALESCE(com.ordenes_compra, 0)          AS ordenes_compra,
       COALESCE(com.valor_compras, 0)           AS valor_compras,
       COALESCE(tr_env.transferencias_enviadas, 0)  AS transferencias_enviadas,
       COALESCE(tr_rec.transferencias_recibidas, 0) AS transferencias_recibidas
FROM ext_organizacion.sedes s
LEFT JOIN inv    ON inv.id_sede    = s.id_sede
LEFT JOIN ped    ON ped.id_sede    = s.id_sede
LEFT JOIN com    ON com.id_sede    = s.id_sede
LEFT JOIN tr_env ON tr_env.id_sede = s.id_sede
LEFT JOIN tr_rec ON tr_rec.id_sede = s.id_sede;
```

## Notas

- **Dónde se ejecuta:** ambos bloques se ejecutan conectado a la base de datos de `reportes`.
- **Azure:** si esa base está en Azure Database for PostgreSQL flexible server, la extensión `postgres_fdw` debe estar habilitada en el parámetro de servidor `azure.extensions`. Además, el servidor donde corre `reportes` necesita llegar por red a los 6 servidores remotos (reglas de firewall mientras el acceso público esté habilitado).
- **Repetir la demostración desde cero:** `DROP SERVER IF EXISTS <nombre>_server CASCADE;` elimina el servidor, su mapeo y sus tablas foráneas.
- **Adaptación de las vistas de referencia:** las vistas se tomaron de `03_vistas_reportes.sql` y se ajustaron al diseño de las bases de datos:
  - se eliminaron las dos vistas base de unión de fragmentos y se consulta directamente la tabla madre particionada;
  - los filtros de estado se ajustaron a los valores reales de los `CHECK`: pagos `'aprobado'`, pedidos `'completado'` (no existe `'confirmado'`) y recepciones `'procesada'` (se excluyen las anuladas);
  - en la vista 9, los pedidos en estado `'devolucion'` también cuentan como vendidos, porque son ventas que luego tuvieron una devolución;
  - en la vista 8, `fecha_despacho` se convierte con `::date` para que `dias_transcurridos` sea un número entero de días;
  - `detalle_pedido` se une a `pedidos_venta` por `(id_pedido, id_sede)`, la clave primaria compuesta de la tabla particionada.
