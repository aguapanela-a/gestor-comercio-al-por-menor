# Punto 9: Arquitectura de Microservicios, Estrategia de Distribución y Seguridad RBAC

**Proyecto final de Bases de Datos — Diseño e implementación de una arquitectura de datos basada en microservicios**

**Integrantes**

- Erick Santiago Buitrago Peña - 20221020072
- Dairo Alejandro Nestiel Muñoz - 20231020025

---

## Contexto de la arquitectura

La capa de persistencia está dividida en **6 bases de datos independientes**, cada una desplegada en su propio recurso *Azure Database for PostgreSQL flexible server* (PostgreSQL 18, región Mexico Central, grupo de recursos `databases-project-microservices`). Este documento define dos decisiones de la arquitectura:

1. **Estrategia de distribución de datos:** fragmentación horizontal por sede mediante **particionamiento declarativo por LISTA** en los dos microservicios de mayor densidad transaccional (`inventarios_db` y `ventas_db`).
2. **Seguridad:** usuarios y permisos nativos de PostgreSQL (`CREATE USER`, `GRANT`) para cada microservicio.

Las cuatro sedes registradas en el sistema, que son también las **claves de partición** (`id_sede`), son:

| `id_sede` | Sede | Partición en `inventarios` | Partición en `pedidos_venta` |
|:---:|---|---|---|
| 1 | Sede Norte | `inventarios_sede_norte` | `pedidos_venta_sede_norte` |
| 2 | Sede Sur | `inventarios_sede_sur` | `pedidos_venta_sede_sur` |
| 3 | Sede Centro | `inventarios_sede_centro` | `pedidos_venta_sede_centro` |
| 4 | Centro de Distribución Nacional | `inventarios_sede_distribucion` | `pedidos_venta_sede_distribucion` |
| — | Cualquier sede nueva o no mapeada | `inventarios_sede_default` | `pedidos_venta_sede_default` |

---

## Sección 1: Fragmentación horizontal mediante particionamiento declarativo (PostgreSQL)

En el particionamiento declarativo, la **tabla madre** no almacena filas: define la estructura y la clave de partición (`PARTITION BY LIST (id_sede)`), y cada **partición** es una tabla física independiente que guarda únicamente las filas de su sede. Para la aplicación, la tabla madre sigue siendo una sola relación lógica; PostgreSQL se encarga de enrutar cada fila a su partición.

> **Regla de PostgreSQL que condiciona el diseño:** toda clave primaria o restricción `UNIQUE` de una tabla particionada **debe incluir la columna de partición**. Por eso las claves primarias de las dos tablas madre incluyen `id_sede`.

### 1.1. Microservicio de Inventarios (`inventarios_db`)

Servidor: `inventarios-db-server` · Esquema: `inventarios`.

**Tabla madre `inventarios` particionada por `id_sede`:**

```sql
-- =============================================================================
-- inventarios_db · Tabla madre particionada por LISTA (id_sede)
-- =============================================================================
CREATE SCHEMA IF NOT EXISTS inventarios;

CREATE TABLE inventarios.inventarios (
    id_sede             INT        NOT NULL,   -- Clave de partición (FKL a organizacion.sedes)
    id_almacen          INT        NOT NULL,   -- FKL a organizacion.almacenes
    id_producto         INT        NOT NULL,   -- FKL a catalogo.productos
    existencia_actual   INT        NOT NULL DEFAULT 0
        CONSTRAINT chk_existencia_no_negativa CHECK (existencia_actual >= 0),
    stock_minimo        INT        NOT NULL DEFAULT 10
        CONSTRAINT chk_stock_min_no_negativo  CHECK (stock_minimo >= 0),
    fecha_actualizacion TIMESTAMP  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    -- La PK de una tabla particionada debe incluir la clave de partición
    CONSTRAINT pk_inventarios PRIMARY KEY (id_sede, id_almacen, id_producto)
) PARTITION BY LIST (id_sede);
```

**Particiones por sede:**

```sql
-- 1. Sede Norte
CREATE TABLE inventarios.inventarios_sede_norte
    PARTITION OF inventarios.inventarios FOR VALUES IN (1);

-- 2. Sede Sur
CREATE TABLE inventarios.inventarios_sede_sur
    PARTITION OF inventarios.inventarios FOR VALUES IN (2);

-- 3. Sede Centro
CREATE TABLE inventarios.inventarios_sede_centro
    PARTITION OF inventarios.inventarios FOR VALUES IN (3);

-- 4. Centro de Distribución Nacional
CREATE TABLE inventarios.inventarios_sede_distribucion
    PARTITION OF inventarios.inventarios FOR VALUES IN (4);

-- 5. Partición por defecto: captura registros de cualquier sede nueva no mapeada
CREATE TABLE inventarios.inventarios_sede_default
    PARTITION OF inventarios.inventarios DEFAULT;
```

### 1.2. Microservicio de Ventas (`ventas_db`)

Servidor: `ventas-db-server` · Esquema: `ventas`.

**Tabla madre `pedidos_venta` particionada por `id_sede`:**

```sql
-- =============================================================================
-- ventas_db · Tabla madre particionada por LISTA (id_sede)
-- Requiere que la tabla ventas.clientes exista previamente.
-- =============================================================================
CREATE SCHEMA IF NOT EXISTS ventas;

CREATE TABLE ventas.pedidos_venta (
    id_pedido        INT           GENERATED ALWAYS AS IDENTITY,
    id_sede          INT           NOT NULL,   -- Clave de partición (FKL a organizacion.sedes)
    id_almacen       INT           NOT NULL,   -- FKL a organizacion.almacenes
    id_cliente       INT           NOT NULL
        CONSTRAINT fk_pedido_cliente REFERENCES ventas.clientes (id_cliente),
    id_empleado      INT           NOT NULL,   -- FKL a identidad.empleados
    fecha_pedido     DATE          NOT NULL DEFAULT CURRENT_DATE,
    estado           VARCHAR(15)   NOT NULL DEFAULT 'pendiente'
        CHECK (estado IN ('pendiente', 'completado', 'cancelado', 'devolucion')),
    total_registrado NUMERIC(14,2) NOT NULL DEFAULT 0.00
        CHECK (total_registrado >= 0),
    -- La PK de una tabla particionada debe incluir la clave de partición
    CONSTRAINT pk_pedidos_venta PRIMARY KEY (id_pedido, id_sede)
) PARTITION BY LIST (id_sede);
```

**Particiones por sede:**

```sql
-- 1. Sede Norte
CREATE TABLE ventas.pedidos_venta_sede_norte
    PARTITION OF ventas.pedidos_venta FOR VALUES IN (1);

-- 2. Sede Sur
CREATE TABLE ventas.pedidos_venta_sede_sur
    PARTITION OF ventas.pedidos_venta FOR VALUES IN (2);

-- 3. Sede Centro
CREATE TABLE ventas.pedidos_venta_sede_centro
    PARTITION OF ventas.pedidos_venta FOR VALUES IN (3);

-- 4. Centro de Distribución Nacional
CREATE TABLE ventas.pedidos_venta_sede_distribucion
    PARTITION OF ventas.pedidos_venta FOR VALUES IN (4);

-- 5. Partición por defecto: cualquier sede futura o no categorizada
CREATE TABLE ventas.pedidos_venta_sede_default
    PARTITION OF ventas.pedidos_venta DEFAULT;
```

**Impacto en las tablas hijas (`detalle_pedido`, `pagos`, `devoluciones`).** Como la clave primaria de `pedidos_venta` ahora es `(id_pedido, id_sede)`, una llave foránea que referencie solo `id_pedido` ya no es válida. La solución recomendada es agregar `id_sede` a cada tabla hija y declarar una **llave foránea compuesta** (PostgreSQL permite llaves foráneas hacia tablas particionadas desde la versión 12). Patrón para `detalle_pedido`; `pagos` y `devoluciones` siguen el mismo esquema:

```sql
CREATE TABLE ventas.detalle_pedido (
    id_pedido       INT           NOT NULL,
    id_sede         INT           NOT NULL,   -- Se propaga para poder referenciar la PK compuesta
    id_producto     INT           NOT NULL,   -- FKL a catalogo.productos
    cantidad        INT           NOT NULL CHECK (cantidad > 0),
    precio_unitario NUMERIC(12,2) NOT NULL CHECK (precio_unitario >= 0),
    PRIMARY KEY (id_pedido, id_producto),
    CONSTRAINT fk_detpedido_pedido FOREIGN KEY (id_pedido, id_sede)
        REFERENCES ventas.pedidos_venta (id_pedido, id_sede) ON DELETE CASCADE
);
```

> **Unicidad de `id_pedido`:** como la clave primaria es compuesta, PostgreSQL no puede garantizar con una restricción que `id_pedido` sea único por sí solo. Esa unicidad la asegura la secuencia de la columna `IDENTITY` (compartida por todas las particiones), y `GENERATED ALWAYS` impide que la aplicación inserte un valor manual.

### 1.3. Guía de implementación en la capa de API / Microservicio

La regla general para cualquier API (Spring Boot, Node o Python) es **trabajar siempre contra la tabla madre** (`inventarios.inventarios`, `ventas.pedidos_venta`) y nunca contra las particiones. El enrutamiento y la selección de fragmentos son responsabilidad del motor, no de la aplicación.

#### Escritura / Inserción

1. La API determina el `id_sede` del registro. Lo recomendable es tomarlo del contexto autenticado del empleado (su sede en `identidad.empleados`) y no del cuerpo de la petición, para que un cliente no pueda escribir en la sede de otro.
2. La API ejecuta `INSERT INTO inventarios.inventarios ...` o `INSERT INTO ventas.pedidos_venta ...` sobre la tabla madre, incluyendo siempre `id_sede`.
3. PostgreSQL compara el valor de `id_sede` con los límites de cada partición (*tuple routing*) y guarda la fila **automáticamente** en la partición física correspondiente. Un `id_sede = 2` termina en `*_sede_sur` sin que la API lo indique.
4. Si el `id_sede` no corresponde a ninguna partición de lista, la fila se almacena en la partición `DEFAULT`. Esta partición actúa como *fallback* de seguridad: sin ella, el `INSERT` fallaría con el error `no partition of relation ... found for row`; con ella, el dato no se pierde y puede auditarse y reubicarse.

Ejemplo en **Spring Boot** (`JdbcTemplate`). La API no envía `id_pedido` porque es `GENERATED ALWAYS`; lo recupera con `RETURNING`:

```java
@Repository
public class PedidoRepository {

    private final JdbcTemplate jdbc;

    public PedidoRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    /** Inserta sobre la tabla MADRE; PostgreSQL enruta a la partición de la sede. */
    public Integer crearPedido(int idSede, int idAlmacen, int idCliente,
                               int idEmpleado, BigDecimal total) {
        return jdbc.queryForObject("""
            INSERT INTO ventas.pedidos_venta
                (id_sede, id_almacen, id_cliente, id_empleado, total_registrado)
            VALUES (?, ?, ?, ?, ?)
            RETURNING id_pedido
            """, Integer.class, idSede, idAlmacen, idCliente, idEmpleado, total);
    }
}
```

#### Lectura / Consultas por sede (*Partition Pruning*)

Cuando la API consulta con el filtro de la clave de partición, por ejemplo:

```sql
SELECT * FROM inventarios.inventarios WHERE id_sede = 2;
```

el optimizador compara el predicado `id_sede = 2` con los límites de cada partición y **descarta** (poda) las que no pueden contener filas que lo cumplan. El resultado es que el motor escanea únicamente `inventarios_sede_sur` y no toca las demás: menos lecturas de disco, índices más pequeños y tiempos de respuesta más estables a medida que crece el volumen.

- **Poda en planificación:** cuando el valor es una constante en la consulta.
- **Poda en ejecución:** cuando el valor llega como parámetro enlazado (`?`, `$1`, `%s`), que es el caso normal en una API que usa consultas parametrizadas.

Para comprobarlo, ejecute `EXPLAIN SELECT * FROM inventarios.inventarios WHERE id_sede = 2;` y verifique que el plan menciona solo la partición `inventarios_sede_sur`. La poda está activa por defecto (`enable_partition_pruning = on`).

Ejemplos de consulta por sede con parámetros enlazados:

```js
// Node.js (node-postgres)
const { rows } = await pool.query(
  `SELECT id_almacen, id_producto, existencia_actual, stock_minimo
     FROM inventarios.inventarios
    WHERE id_sede = $1`,
  [idSede]
);
```

```python
# Python (psycopg)
cur.execute(
    """SELECT id_pedido, fecha_pedido, estado, total_registrado
         FROM ventas.pedidos_venta
        WHERE id_sede = %s AND estado = %s""",
    (id_sede, "pendiente"),
)
```

#### Buenas prácticas para la API

| Práctica | Motivo |
|---|---|
| Incluir `id_sede` en el `WHERE` de todo `SELECT`, `UPDATE` y `DELETE` | Sin ese filtro no hay poda y el motor recorre las 5 particiones. |
| No apuntar directamente a `inventarios_sede_*` ni `pedidos_venta_sede_*` | Acopla la API a detalles físicos; si se agrega una sede, el código no debería cambiar. |
| Usar siempre consultas parametrizadas | Evita inyección SQL y permite la poda en ejecución. |
| No modificar el `id_sede` de una fila existente | Obligaría a PostgreSQL a moverla de una partición a otra. |
| Monitorear la partición `DEFAULT` (`SELECT count(*) FROM inventarios.inventarios_sede_default;`) | Si tiene filas, hay registros de una sede no mapeada que requieren atención. |

#### Alta de una nueva sede

1. Registrar la sede en `organizacion.sedes` (microservicio `organizacion`).
2. Si ya hay filas de ese `id_sede` en la partición `DEFAULT`, moverlas fuera antes de continuar: PostgreSQL verifica que `DEFAULT` no contenga filas que pertenezcan a la nueva partición y, si las hay, rechaza la creación.
3. Crear la partición con `CREATE TABLE ... PARTITION OF ... FOR VALUES IN (n)` en `inventarios` y en `pedidos_venta`, reinsertar las filas movidas y otorgar los permisos de la Sección 2 sobre las nuevas tablas.

#### Relación con la capa `reportes`

Con particionamiento declarativo, la tabla madre ya presenta los cuatro fragmentos como una sola relación. Las vistas base de la capa de reportes (`vista_inventarios_consolidado` y `vista_pedidos_consolidado`) pueden leer directamente la tabla madre en lugar de unir manualmente los fragmentos con `UNION ALL`.

---

## Sección 2: Control de accesos, usuarios y permisos (Script SQL unificado)

El script crea **2 usuarios por cada base de datos** (12 en total):

| # | Base de datos | Servidor | Esquema | Usuario propietario (microservicio dueño) | Usuario de integración FDW |
|:---:|---|---|---|---|---|
| 1 | `catalogo_db` | `catalogo-db-server` | `catalogo` | `user_catalogo` | `user_pg_fdw` |
| 2 | `organizacion_db` | `organizacion-db-server` | `organizacion` | `user_organizacion` | `user_pg_fdw` |
| 3 | `compras_db` | `compras-db-server` | `compras` | `user_compras` | `user_pg_fdw` |
| 4 | `inventarios_db` | `inventarios-db-server` | `inventarios` | `user_inventarios` | `user_pg_fdw` |
| 5 | `ventas_db` | `ventas-db-server` | `ventas` | `user_ventas` | `user_pg_fdw` |
| 6 | `identidad_db` | `identidad-db-server` | `identidad` | `user_identidad` | `user_pg_fdw` |

| Usuario | Privilegios | Alcance |
|---|---|---|
| `user_{microservicio}` | `SELECT, INSERT, UPDATE, DELETE` (CRUD completo) | Todas las tablas del esquema de su microservicio |
| `user_pg_fdw` | `SELECT, UPDATE` (lectura y actualización) | Todas las tablas del esquema de su microservicio |

**Cómo ejecutar el script.** Como cada base de datos reside en un servidor de Azure distinto, los usuarios (roles) son propios de cada servidor: `user_pg_fdw` se crea una vez en cada uno de los 6 servidores, con credenciales independientes. Además, `GRANT USAGE ON SCHEMA` y `GRANT ... ON ALL TABLES` solo afectan a la base de datos a la que se está conectado. Por eso cada sección del script debe ejecutarse conectado al servidor y a la base de datos indicados en su encabezado, con el usuario administrador del servidor. Si se usa `psql`, puede descomentarse la línea `\c` de cada sección (reemplazando `<ADMIN>`) para cambiar de servidor dentro del mismo archivo. El script debe ejecutarse **después** de crear las tablas (DDL), porque `ON ALL TABLES` solo cubre las tablas existentes en ese momento.

```sql
-- =============================================================================
-- CONTROL DE ACCESOS · USUARIOS Y PERMISOS · 6 MICROSERVICIOS (12 USUARIOS)
-- Ejecutar cada sección conectado al servidor y a la base de datos indicados,
-- con el usuario administrador del servidor Azure PostgreSQL flexible server.
-- Las contraseñas son de PRUEBA: en un entorno real se gestionan con un
-- gestor de secretos (por ejemplo, Azure Key Vault) y no se versionan.
-- =============================================================================


-- =============================================================================
-- 1. MICROSERVICIO: CATÁLOGO
-- Servidor: catalogo-db-server | Base de datos: catalogo_db | Esquema: catalogo
-- user_catalogo -> propietario del microservicio (CRUD completo)
-- user_pg_fdw   -> integración FDW (lectura y actualización)
-- =============================================================================
-- \c "host=catalogo-db-server.postgres.database.azure.com port=5432 dbname=catalogo_db user=<ADMIN> sslmode=require"

-- Creación de usuarios
CREATE USER user_catalogo WITH PASSWORD 'Ctl_Own#2026!aK9';
CREATE USER user_pg_fdw   WITH PASSWORD 'Ctl_Fdw#2026!mR4';

-- Permiso de conexión a la base de datos
GRANT CONNECT ON DATABASE catalogo_db TO user_catalogo;
GRANT CONNECT ON DATABASE catalogo_db TO user_pg_fdw;

-- Permiso de uso sobre el esquema
GRANT USAGE ON SCHEMA catalogo TO user_catalogo;
GRANT USAGE ON SCHEMA catalogo TO user_pg_fdw;

-- Permisos sobre las tablas del esquema
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA catalogo TO user_catalogo;  -- CRUD completo
GRANT SELECT, UPDATE                 ON ALL TABLES IN SCHEMA catalogo TO user_pg_fdw;    -- RU
GRANT USAGE ON ALL SEQUENCES IN SCHEMA catalogo TO user_catalogo;                        -- Secuencias del propietario


-- =============================================================================
-- 2. MICROSERVICIO: ORGANIZACIÓN
-- Servidor: organizacion-db-server | Base de datos: organizacion_db | Esquema: organizacion
-- user_organizacion -> propietario del microservicio (CRUD completo)
-- user_pg_fdw       -> integración FDW (lectura y actualización)
-- =============================================================================
-- \c "host=organizacion-db-server.postgres.database.azure.com port=5432 dbname=organizacion_db user=<ADMIN> sslmode=require"

-- Creación de usuarios
CREATE USER user_organizacion WITH PASSWORD 'Org_Own#2026!bT7';
CREATE USER user_pg_fdw       WITH PASSWORD 'Org_Fdw#2026!nS2';

-- Permiso de conexión a la base de datos
GRANT CONNECT ON DATABASE organizacion_db TO user_organizacion;
GRANT CONNECT ON DATABASE organizacion_db TO user_pg_fdw;

-- Permiso de uso sobre el esquema
GRANT USAGE ON SCHEMA organizacion TO user_organizacion;
GRANT USAGE ON SCHEMA organizacion TO user_pg_fdw;

-- Permisos sobre las tablas del esquema
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA organizacion TO user_organizacion;  -- CRUD completo
GRANT SELECT, UPDATE                 ON ALL TABLES IN SCHEMA organizacion TO user_pg_fdw;        -- RU
GRANT USAGE ON ALL SEQUENCES IN SCHEMA organizacion TO user_organizacion;                        -- Secuencias del propietario


-- =============================================================================
-- 3. MICROSERVICIO: COMPRAS
-- Servidor: compras-db-server | Base de datos: compras_db | Esquema: compras
-- user_compras -> propietario del microservicio (CRUD completo)
-- user_pg_fdw  -> integración FDW (lectura y actualización)
-- =============================================================================
-- \c "host=compras-db-server.postgres.database.azure.com port=5432 dbname=compras_db user=<ADMIN> sslmode=require"

-- Creación de usuarios
CREATE USER user_compras WITH PASSWORD 'Cmp_Own#2026!cW5';
CREATE USER user_pg_fdw  WITH PASSWORD 'Cmp_Fdw#2026!pV8';

-- Permiso de conexión a la base de datos
GRANT CONNECT ON DATABASE compras_db TO user_compras;
GRANT CONNECT ON DATABASE compras_db TO user_pg_fdw;

-- Permiso de uso sobre el esquema
GRANT USAGE ON SCHEMA compras TO user_compras;
GRANT USAGE ON SCHEMA compras TO user_pg_fdw;

-- Permisos sobre las tablas del esquema
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA compras TO user_compras;  -- CRUD completo
GRANT SELECT, UPDATE                 ON ALL TABLES IN SCHEMA compras TO user_pg_fdw;   -- RU
GRANT USAGE ON ALL SEQUENCES IN SCHEMA compras TO user_compras;                        -- Secuencias del propietario


-- =============================================================================
-- 4. MICROSERVICIO: INVENTARIOS (tabla inventarios particionada por id_sede)
-- Servidor: inventarios-db-server | Base de datos: inventarios_db | Esquema: inventarios
-- user_inventarios -> propietario del microservicio (CRUD completo)
-- user_pg_fdw      -> integración FDW (lectura y actualización)
-- ON ALL TABLES incluye la tabla madre y todas sus particiones.
-- =============================================================================
-- \c "host=inventarios-db-server.postgres.database.azure.com port=5432 dbname=inventarios_db user=<ADMIN> sslmode=require"

-- Creación de usuarios
CREATE USER user_inventarios WITH PASSWORD 'Inv_Own#2026!dX3';
CREATE USER user_pg_fdw      WITH PASSWORD 'Inv_Fdw#2026!qY6';

-- Permiso de conexión a la base de datos
GRANT CONNECT ON DATABASE inventarios_db TO user_inventarios;
GRANT CONNECT ON DATABASE inventarios_db TO user_pg_fdw;

-- Permiso de uso sobre el esquema
GRANT USAGE ON SCHEMA inventarios TO user_inventarios;
GRANT USAGE ON SCHEMA inventarios TO user_pg_fdw;

-- Permisos sobre las tablas del esquema
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA inventarios TO user_inventarios;  -- CRUD completo
GRANT SELECT, UPDATE                 ON ALL TABLES IN SCHEMA inventarios TO user_pg_fdw;       -- RU
GRANT USAGE ON ALL SEQUENCES IN SCHEMA inventarios TO user_inventarios;                        -- Secuencias del propietario


-- =============================================================================
-- 5. MICROSERVICIO: VENTAS (tabla pedidos_venta particionada por id_sede)
-- Servidor: ventas-db-server | Base de datos: ventas_db | Esquema: ventas
-- user_ventas -> propietario del microservicio (CRUD completo)
-- user_pg_fdw -> integración FDW (lectura y actualización)
-- ON ALL TABLES incluye la tabla madre y todas sus particiones.
-- =============================================================================
-- \c "host=ventas-db-server.postgres.database.azure.com port=5432 dbname=ventas_db user=<ADMIN> sslmode=require"

-- Creación de usuarios
CREATE USER user_ventas WITH PASSWORD 'Vta_Own#2026!eZ1';
CREATE USER user_pg_fdw WITH PASSWORD 'Vta_Fdw#2026!rU4';

-- Permiso de conexión a la base de datos
GRANT CONNECT ON DATABASE ventas_db TO user_ventas;
GRANT CONNECT ON DATABASE ventas_db TO user_pg_fdw;

-- Permiso de uso sobre el esquema
GRANT USAGE ON SCHEMA ventas TO user_ventas;
GRANT USAGE ON SCHEMA ventas TO user_pg_fdw;

-- Permisos sobre las tablas del esquema
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA ventas TO user_ventas;  -- CRUD completo
GRANT SELECT, UPDATE                 ON ALL TABLES IN SCHEMA ventas TO user_pg_fdw;  -- RU
GRANT USAGE ON ALL SEQUENCES IN SCHEMA ventas TO user_ventas;                        -- Secuencias del propietario


-- =============================================================================
-- 6. MICROSERVICIO: IDENTIDAD
-- Servidor: identidad-db-server | Base de datos: identidad_db | Esquema: identidad
-- user_identidad -> propietario del microservicio (CRUD completo)
-- user_pg_fdw    -> integración FDW (lectura y actualización)
-- =============================================================================
-- \c "host=identidad-db-server.postgres.database.azure.com port=5432 dbname=identidad_db user=<ADMIN> sslmode=require"

-- Creación de usuarios
CREATE USER user_identidad WITH PASSWORD 'Idn_Own#2026!fH8';
CREATE USER user_pg_fdw    WITH PASSWORD 'Idn_Fdw#2026!sJ3';

-- Permiso de conexión a la base de datos
GRANT CONNECT ON DATABASE identidad_db TO user_identidad;
GRANT CONNECT ON DATABASE identidad_db TO user_pg_fdw;

-- Permiso de uso sobre el esquema
GRANT USAGE ON SCHEMA identidad TO user_identidad;
GRANT USAGE ON SCHEMA identidad TO user_pg_fdw;

-- Permisos sobre las tablas del esquema
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA identidad TO user_identidad;  -- CRUD completo
GRANT SELECT, UPDATE                 ON ALL TABLES IN SCHEMA identidad TO user_pg_fdw;     -- RU
GRANT USAGE ON ALL SEQUENCES IN SCHEMA identidad TO user_identidad;                        -- Secuencias del propietario
```

### Consideraciones de seguridad y operación

- **Prerrequisitos:** los esquemas `compras`, `inventarios` y `ventas` deben existir y contener las tablas de su microservicio antes de ejecutar los `GRANT`.
- **Tablas y particiones nuevas:** `GRANT ... ON ALL TABLES` solo cubre las tablas existentes. Cuando se cree una partición o una tabla nueva (por ejemplo, al dar de alta una sede), debe repetirse el `GRANT` sobre ella o configurarse `ALTER DEFAULT PRIVILEGES` para el usuario que crea los objetos.
- **Uso de `user_pg_fdw`:** es el usuario que la capa `reportes` utiliza en el `USER MAPPING` de `postgres_fdw` para consultar cada servidor. En Azure Database for PostgreSQL flexible server, la extensión `postgres_fdw` debe habilitarse previamente en el parámetro de servidor `azure.extensions`.
- **`DELETE` y eliminación lógica:** el usuario propietario recibe `DELETE` por requerimiento, pero la regla de negocio institucional establece que ninguna entidad operativa se destruye físicamente y que la baja se hace con `estado = 'INACTIVO'`. Esa regla debe aplicarse en la capa de API.
- **Datos sensibles en `identidad`:** con `SELECT` sobre todo el esquema, `user_pg_fdw` puede leer `usuarios.password_hash`. Si la capa `reportes` no lo necesita, conviene restringirlo con privilegios por columna.
- **Contraseñas:** las del script son de prueba. Antes de publicar este documento o de pasar a un entorno real, deben reemplazarse por secretos gestionados fuera del repositorio.