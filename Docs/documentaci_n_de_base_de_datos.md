# Scripts SQL DDL y DML

**Integrantes**

- Erick Santiago Buitrago Peña - 20221020072
- Dairo Alejandro Nestiel Muñoz - 20231020025

---

## Despliegue en Azure

Cada una de las bases de datos está desplegada en un recurso **Azure Database for PostgreSQL flexible server** de Azure, y todos los recursos pertenecen a un mismo grupo de recursos. Se habilitó acceso público de forma **temporal** únicamente para ejecutar los scripts desde las máquinas locales y realizar las demostraciones. Una vez finalizada esta etapa, cada base de datos solo podrá ser accedida desde la API del microservicio correspondiente.

| Microservicio | Servidor | Base de datos |
|---|---|---|
| Catálogo | `catalogo-db-server` | `catalogo_db` |
| Organización | `organizacion-db-server` | `organizacion_db` |
| Compras | `compras-db-server` | `compras_db` |
| Inventarios | `inventarios-db-server` | `inventarios_db` |
| Ventas | `ventas-db-server` | `ventas_db` |
| Identidad | `identidad-db-server` | `identidad_db` |

A continuación se documenta la creación de la base de datos de cada microservicio: una breve descripción, la creación de tablas (DDL), la inserción de datos de prueba (DML) y las vistas y consultas de verificación.

---

## 1. Catálogo (`catalogo`)

> Gestiona la metadata maestra del producto: qué vende la empresa, cómo se clasifica y en qué unidad se mide.

### 1.1 Creación de tablas (DDL)

Se crea el esquema `catalogo` con dos tablas: `categorias` y `productos`. Cada tabla usa una columna de identidad como llave primaria, y `productos` referencia a `categorias` mediante una llave foránea. Se aplican restricciones `UNIQUE` (nombre de categoría y SKU) y `CHECK` (estados válidos y precio de lista no negativo) para proteger la integridad de los datos.

```sql
--- creacion de tablas catalogo ---
CREATE SCHEMA IF NOT EXISTS catalogo;

CREATE TABLE IF NOT EXISTS catalogo.categorias (
    id_categoria INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre       VARCHAR(80)  NOT NULL UNIQUE,
    descripcion  VARCHAR(200),
    estado       VARCHAR(10)  NOT NULL DEFAULT 'activo' CHECK (estado IN ('activo','inactivo'))
);

CREATE TABLE IF NOT EXISTS catalogo.productos (
    id_producto   INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sku           VARCHAR(30)  NOT NULL UNIQUE,
    nombre        VARCHAR(120) NOT NULL,
    id_categoria  INTEGER      NOT NULL REFERENCES catalogo.categorias (id_categoria),
    unidad_medida VARCHAR(20)  NOT NULL,
    precio_lista  NUMERIC(12,2) NOT NULL CHECK (precio_lista >= 0),
    estado        VARCHAR(10)  NOT NULL CHECK (estado IN ('activo','inactivo'))
);
```

### 1.2 Inserción de datos (DML)

Se vacían las tablas con `TRUNCATE ... RESTART IDENTITY` y se insertan 9 categorías y 85 productos, fijando los id con `OVERRIDING SYSTEM VALUE`. Los productos 1 a 80 son artículos de consumo masivo (algunos inactivos) y los productos 101 a 105 son los que ya usan compras e inventarios. Al final, `setval` sincroniza las secuencias de identidad con el mayor id insertado.

```sql
--- generación de datos catalogo ---


TRUNCATE catalogo.productos, catalogo.categorias RESTART IDENTITY;

INSERT INTO catalogo.categorias (id_categoria, nombre, descripcion, estado)
OVERRIDING SYSTEM VALUE VALUES
(1, 'Granos y Cereales', 'Arroz, leguminosas, pastas, harinas y azúcar',          'activo'),
(2, 'Aceites y Grasas',  'Aceites comestibles, margarinas y mantecas',            'activo'),
(3, 'Lácteos y Huevos',  'Leches, yogures, quesos, mantequilla y huevos',         'activo'),
(4, 'Bebidas',           'Aguas, gaseosas, jugos, café y chocolate',              'activo'),
(5, 'Aseo del Hogar',    'Detergentes, limpiadores y artículos de limpieza',      'activo'),
(6, 'Cuidado Personal',  'Higiene y cuidado personal',                            'activo'),
(7, 'Mascotas',          'Alimentos y accesorios para mascotas (aún sin productos)', 'activo'),
(8, 'Tecnología y Accesorios', 'Periféricos, monitores y accesorios de cómputo',   'activo'),
(9, 'Dotación y Uniformes',    'Uniformes y dotación corporativa',                'activo');

INSERT INTO catalogo.productos (id_producto, sku, nombre, id_categoria, unidad_medida, precio_lista, estado)
OVERRIDING SYSTEM VALUE VALUES
-- Granos y Cereales
(1,  'GRA-ARR-500',      'Arroz blanco 500 g',          1, 'unidad',  2800.00, 'activo'),
(2,  'GRA-ARR-1000',     'Arroz blanco 1 kg',           1, 'unidad',  5200.00, 'activo'),
(3,  'GRA-ARR-INT-500',  'Arroz integral 500 g',        1, 'unidad',  3900.00, 'activo'),
(4,  'GRA-FRI-500',      'Fríjol cargamanto 500 g',     1, 'unidad',  6800.00, 'activo'),
(5,  'GRA-LEN-500',      'Lentejas 500 g',              1, 'unidad',  4100.00, 'activo'),
(6,  'GRA-GAR-500',      'Garbanzo 500 g',              1, 'unidad',  5600.00, 'activo'),
(7,  'GRA-MAI-500',      'Maíz pira 500 g',             1, 'unidad',  3500.00, 'activo'),
(8,  'GRA-AVE-400',      'Avena en hojuelas 400 g',     1, 'unidad',  3300.00, 'activo'),
(9,  'GRA-CEB-500',      'Cebada perlada 500 g',        1, 'unidad',  2900.00, 'activo'),
(10, 'GRA-PAS-250',      'Pasta espagueti 250 g',       1, 'unidad',  2200.00, 'activo'),
(11, 'GRA-PAS-500',      'Pasta espagueti 500 g',       1, 'unidad',  3800.00, 'activo'),
(12, 'GRA-HAR-1000',     'Harina de trigo 1 kg',        1, 'unidad',  4200.00, 'activo'),
(13, 'GRA-AZU-GRA',      'Azúcar blanca a granel',      1, 'kg',      4600.00, 'activo'),
(14, 'GRA-QUI-500',      'Quinua 500 g',                1, 'unidad', 11500.00, 'inactivo'),
-- Aceites y Grasas
(15, 'ACE-GIR-900',      'Aceite de girasol 900 ml',    2, 'unidad', 14500.00, 'activo'),
(16, 'ACE-GIR-3000',     'Aceite de girasol 3 L',       2, 'unidad', 41500.00, 'activo'),
(17, 'ACE-SOY-900',      'Aceite de soya 900 ml',       2, 'unidad', 12900.00, 'activo'),
(18, 'ACE-OLI-250',      'Aceite de oliva extra virgen 250 ml', 2, 'unidad', 22900.00, 'activo'),
(19, 'ACE-OLI-500',      'Aceite de oliva extra virgen 500 ml', 2, 'unidad', 38900.00, 'activo'),
(20, 'ACE-COC-500',      'Aceite de coco 500 ml',       2, 'unidad', 27500.00, 'activo'),
(21, 'ACE-MAR-250',      'Margarina 250 g',             2, 'unidad',  4800.00, 'activo'),
(22, 'ACE-MAR-500',      'Margarina 500 g',             2, 'unidad',  8900.00, 'activo'),
(23, 'ACE-MAN-500',      'Manteca vegetal 500 g',       2, 'unidad',  7200.00, 'activo'),
(24, 'ACE-AGU-250',      'Aceite de aguacate 250 ml',   2, 'unidad', 29900.00, 'inactivo'),
-- Lácteos y Huevos
(25, 'LAC-LEC-1000',     'Leche entera 1 L',            3, 'unidad',  4300.00, 'activo'),
(26, 'LAC-LEC-DES-1000', 'Leche deslactosada 1 L',      3, 'unidad',  4900.00, 'activo'),
(27, 'LAC-LEC-SEM-1000', 'Leche semidescremada 1 L',    3, 'unidad',  4500.00, 'activo'),
(28, 'LAC-LEC-POL-380',  'Leche en polvo 380 g',        3, 'unidad', 16900.00, 'activo'),
(29, 'LAC-YOG-1000',     'Yogur natural 1 L',           3, 'unidad',  8200.00, 'activo'),
(30, 'LAC-YOG-FRE-200',  'Yogur de fresa 200 g',        3, 'unidad',  2900.00, 'activo'),
(31, 'LAC-QUE-CAM-500',  'Queso campesino 500 g',       3, 'unidad', 14500.00, 'activo'),
(32, 'LAC-QUE-MOZ-400',  'Queso mozzarella 400 g',      3, 'unidad', 17800.00, 'activo'),
(33, 'LAC-MAN-125',      'Mantequilla 125 g',           3, 'unidad',  5400.00, 'activo'),
(34, 'LAC-CRE-250',      'Crema de leche 250 ml',       3, 'unidad',  5200.00, 'activo'),
(35, 'LAC-KUM-1000',     'Kumis 1 L',                   3, 'unidad',  7800.00, 'activo'),
(36, 'LAC-HUE-30',       'Huevos AA cubeta x30',        3, 'cubeta', 16800.00, 'activo'),
(37, 'LAC-HUE-12',       'Huevos AA docena',            3, 'docena',  7400.00, 'activo'),
(38, 'LAC-ALM-1000',     'Bebida de almendras 1 L',     3, 'unidad',  7900.00, 'inactivo'),
-- Bebidas
(39, 'BEB-AGU-600',      'Agua sin gas 600 ml',         4, 'unidad',  2100.00, 'activo'),
(40, 'BEB-AGU-GAS-600',  'Agua con gas 600 ml',         4, 'unidad',  2400.00, 'activo'),
(41, 'BEB-AGU-5000',     'Agua sin gas bidón 5 L',      4, 'unidad',  7500.00, 'activo'),
(42, 'BEB-GAS-COL-400',  'Gaseosa cola 400 ml',         4, 'unidad',  2600.00, 'activo'),
(43, 'BEB-GAS-COL-1500', 'Gaseosa cola 1,5 L',          4, 'unidad',  5800.00, 'activo'),
(44, 'BEB-GAS-LIM-1500', 'Gaseosa limón 1,5 L',         4, 'unidad',  5600.00, 'activo'),
(45, 'BEB-GAS-NAR-2500', 'Gaseosa naranja 2,5 L',       4, 'unidad',  6900.00, 'activo'),
(46, 'BEB-JUG-NAR-1000', 'Jugo de naranja 1 L',         4, 'unidad',  6200.00, 'activo'),
(47, 'BEB-JUG-MAN-1000', 'Jugo de mango 1 L',           4, 'unidad',  6200.00, 'activo'),
(48, 'BEB-JUG-CAJ-200',  'Jugo en caja 200 ml',         4, 'unidad',  1800.00, 'activo'),
(49, 'BEB-TEF-LIM-500',  'Té frío limón 500 ml',        4, 'unidad',  3500.00, 'activo'),
(50, 'BEB-ENE-250',      'Bebida energizante 250 ml',   4, 'unidad',  4900.00, 'activo'),
(51, 'BEB-CAF-MOL-250',  'Café molido 250 g',           4, 'unidad', 11900.00, 'activo'),
(52, 'BEB-CAF-INS-170',  'Café instantáneo 170 g',      4, 'unidad', 17500.00, 'activo'),
(53, 'BEB-CHO-500',      'Chocolate de mesa 500 g',     4, 'unidad',  9800.00, 'activo'),
(54, 'BEB-ISO-500',      'Bebida isotónica 500 ml',     4, 'unidad',  3900.00, 'inactivo'),
-- Aseo del Hogar
(55, 'ASE-DET-POL-1000', 'Detergente en polvo 1 kg',    5, 'unidad',  9800.00, 'activo'),
(56, 'ASE-DET-LIQ-1500', 'Detergente líquido 1,5 L',    5, 'unidad', 19900.00, 'activo'),
(57, 'ASE-SUA-1000',     'Suavizante de ropa 1 L',      5, 'unidad',  8700.00, 'activo'),
(58, 'ASE-LAV-CRE-500',  'Lavaplatos en crema 500 g',   5, 'unidad',  5300.00, 'activo'),
(59, 'ASE-LAV-LIQ-750',  'Lavaplatos líquido 750 ml',   5, 'unidad',  7400.00, 'activo'),
(60, 'ASE-LIM-1000',     'Limpiador multiusos 1 L',     5, 'unidad',  6900.00, 'activo'),
(61, 'ASE-DES-1000',     'Desinfectante de pisos 1 L',  5, 'unidad',  7200.00, 'activo'),
(62, 'ASE-BLA-1000',     'Blanqueador 1 L',             5, 'unidad',  3900.00, 'activo'),
(63, 'ASE-JAB-BAR-3',    'Jabón de barra para ropa x3', 5, 'paquete', 6200.00, 'activo'),
(64, 'ASE-ESC-3',        'Esponjas lavaplatos x3',      5, 'paquete', 4500.00, 'activo'),
(65, 'ASE-TRA-1',        'Trapero de algodón',          5, 'unidad',  9500.00, 'activo'),
(66, 'ASE-BOL-10',       'Bolsas de basura x10',        5, 'paquete', 5100.00, 'activo'),
(67, 'ASE-PAP-12',       'Papel higiénico x12 rollos',  5, 'paquete', 18900.00, 'activo'),
(68, 'ASE-SER-100',      'Servilletas x100',            5, 'paquete', 2700.00, 'inactivo'),
-- Cuidado Personal
(69, 'CUI-SHA-400',      'Champú 400 ml',               6, 'unidad', 14900.00, 'activo'),
(70, 'CUI-ACO-400',      'Acondicionador 400 ml',       6, 'unidad', 15500.00, 'activo'),
(71, 'CUI-JAB-LIQ-250',  'Jabón líquido de manos 250 ml', 6, 'unidad', 6400.00, 'activo'),
(72, 'CUI-JAB-TOC-3',    'Jabón de tocador x3',         6, 'paquete', 7800.00, 'activo'),
(73, 'CUI-CRE-DEN-75',   'Crema dental 75 ml',          6, 'unidad',  5900.00, 'activo'),
(74, 'CUI-CEP-1',        'Cepillo dental',              6, 'unidad',  3800.00, 'activo'),
(75, 'CUI-DES-50',       'Desodorante en barra 50 g',   6, 'unidad',  8900.00, 'activo'),
(76, 'CUI-CRE-COR-200',  'Crema corporal 200 ml',       6, 'unidad', 12900.00, 'activo'),
(77, 'CUI-PRO-SOL-120',  'Protector solar FPS 50 120 ml', 6, 'unidad', 38900.00, 'activo'),
(78, 'CUI-ESP-AFE-250',  'Espuma de afeitar 250 ml',    6, 'unidad', 11900.00, 'activo'),
(79, 'CUI-TOA-20',       'Toallas higiénicas x20',      6, 'paquete', 8900.00, 'activo'),
(80, 'CUI-ENJ-250',      'Enjuague bucal 250 ml',       6, 'unidad',  9600.00, 'inactivo'),
-- Productos que ya usan compras e inventarios
(101, 'TEC-TEC-RGB',     'Teclado Mecánico RGB',        8, 'unidad',   189900.00, 'activo'),
(102, 'TEC-MON-27-144',  'Monitor Gamer 27" 144Hz',     8, 'unidad',  1199900.00, 'activo'),
(103, 'BEB-PAC-ENE-6',   'Pack de Bebidas Energizantes',4, 'paquete',   36900.00, 'activo'),
(104, 'ASE-KIT-IND',     'Kit de Limpieza Industrial',  5, 'unidad',   124900.00, 'activo'),
(105, 'DOT-UNI-ALG',     'Uniforme Corporativo Algodón',9, 'unidad',    89900.00, 'activo');

SELECT setval(pg_get_serial_sequence('catalogo.categorias', 'id_categoria'), (SELECT max(id_categoria) FROM catalogo.categorias));
SELECT setval(pg_get_serial_sequence('catalogo.productos',  'id_producto'),  (SELECT max(id_producto)  FROM catalogo.productos));
```

### 1.3 Vistas y consultas

**Conteos.** Muestra cuántas filas hay en `categorias` y `productos`, y cuántos productos están activos e inactivos.

```sql
--- vistas catalogo ----



-- Conteos
SELECT 'categorias' AS tabla, count(*) AS filas FROM catalogo.categorias
UNION ALL SELECT 'productos', count(*) FROM catalogo.productos
UNION ALL SELECT 'productos activos', count(*) FROM catalogo.productos WHERE estado = 'activo'
UNION ALL SELECT 'productos inactivos', count(*) FROM catalogo.productos WHERE estado = 'inactivo';
```

**Productos por categoría.** Lista cada categoría con la cantidad de productos que contiene, incluidas las que aún no tienen ninguno.

```sql
-- Productos por categoría.

SELECT c.id_categoria, c.nombre, count(p.id_producto) AS productos
FROM catalogo.categorias c LEFT JOIN catalogo.productos p ON p.id_categoria = c.id_categoria
GROUP BY c.id_categoria, c.nombre ORDER BY c.id_categoria;
```

**Productos usados por compras e inventarios.** Muestra id, SKU, nombre y precio de lista de los productos 101 a 105.

```sql
-- Productos que ya usan compras e inventarios 
SELECT id_producto, sku, nombre, precio_lista FROM catalogo.productos
WHERE id_producto IN (101, 102, 103, 104, 105) ORDER BY id_producto;
```

**Productos inactivos.** Lista el id, el SKU y el nombre de los productos con estado `inactivo`.

```sql
-- Productos inactivos
SELECT id_producto, sku, nombre FROM catalogo.productos WHERE estado = 'inactivo' ORDER BY id_producto;
```

**Pruebas de restricciones.** Ejecuta cuatro sentencias que violan a propósito las restricciones `UNIQUE`, `CHECK` y la llave foránea, y que deben terminar en error.

```sql
-- Pruebas de restricciones
INSERT INTO catalogo.productos (sku,nombre,id_categoria,unidad_medida,precio_lista,estado) VALUES ('GRA-ARR-500','Repetido',1,'unidad',2800,'activo');  -- UNIQUE (SKU duplicado)
INSERT INTO catalogo.productos (sku,nombre,id_categoria,unidad_medida,precio_lista,estado) VALUES ('T-NEG','Prueba',1,'unidad',-100,'activo');          -- CHECK (precio negativo)
INSERT INTO catalogo.productos (sku,nombre,id_categoria,unidad_medida,precio_lista,estado) VALUES ('T-FK','Prueba',999,'unidad',1000,'activo');         -- FK (categoría inexistente)
UPDATE catalogo.productos SET estado = 'borrado' WHERE id_producto = 1;                                                                                 -- CHECK IN (estado)
```

**Eliminación lógica.** Marca el producto 13 como `inactivo` en lugar de borrarlo con `DELETE`.

```sql
-- Eliminación lógica (en lugar de DELETE):
UPDATE catalogo.productos SET estado = 'inactivo' WHERE id_producto = 13;
```

---

## 2. Organización (`organizacion`)

> Administra la infraestructura física y logística: las sedes comerciales, el centro de distribución y los almacenes o bodegas de cada sede.

### 2.1 Creación de tablas (DDL)

Se crea el esquema `organizacion` dentro de una transacción (`BEGIN`/`COMMIT`) con dos tablas: `sedes`, con nombre único, ciudad, dirección y tipo (`comercial` o `distribucion`), y `almacenes`, que pertenece a una sede mediante llave foránea. Cada almacén tiene un tipo (`principal`, `venta` o `recepcion`), la pareja sede–nombre es única y los estados y tipos se controlan con restricciones `CHECK`.

```sql
---___ creacion de tablas organizacion ---
BEGIN;
CREATE SCHEMA IF NOT EXISTS organizacion;

CREATE TABLE IF NOT EXISTS organizacion.sedes (
    id_sede   INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre    VARCHAR(80)  NOT NULL UNIQUE,
    ciudad    VARCHAR(60)  NOT NULL,
    direccion VARCHAR(120) NOT NULL,
    tipo_sede VARCHAR(15)  NOT NULL CHECK (tipo_sede IN ('comercial','distribucion')),
    estado    VARCHAR(10)  NOT NULL CHECK (estado IN ('activo','inactivo'))
);

CREATE TABLE IF NOT EXISTS organizacion.almacenes (
    id_almacen   INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_sede      INTEGER      NOT NULL REFERENCES organizacion.sedes (id_sede),
    nombre       VARCHAR(80)  NOT NULL,
    tipo_almacen VARCHAR(20)  NOT NULL CHECK (tipo_almacen IN ('principal','venta','recepcion')),
    estado       VARCHAR(10)  NOT NULL CHECK (estado IN ('activo','inactivo')),
    UNIQUE (id_sede, nombre)
);
COMMIT;
```

### 2.2 Inserción de datos (DML)

En una transacción se vacían las tablas y se insertan 4 sedes (Bogotá, Cali, Medellín y el Centro de Distribución Nacional en Barranquilla) y 8 almacenes distribuidos entre ellas, fijando los id con `OVERRIDING SYSTEM VALUE`. Al final se sincronizan las secuencias de identidad con `setval`. Los almacenes 1, 2 y 3 son los que ya usan los módulos de compras e inventarios.

```sql
--- adicionde datos de la organización ---

BEGIN;

TRUNCATE organizacion.almacenes, organizacion.sedes RESTART IDENTITY;

INSERT INTO organizacion.sedes (id_sede, nombre, ciudad, direccion, tipo_sede, estado)
OVERRIDING SYSTEM VALUE VALUES
(1, 'Sede Bogotá',                    'Bogotá',       'Calle 19 # 7-30',                        'comercial',    'activo'),
(2, 'Sede Cali',                      'Cali',         'Avenida 6 Norte # 28-45',                'comercial',    'activo'),
(3, 'Sede Medellín',                  'Medellín',     'Carrera 43A # 14-50',                    'comercial',    'activo'),
(4, 'Centro de Distribución Nacional','Barranquilla', 'Km 5 vía Circunvalar, Zona Industrial',  'distribucion', 'activo');

INSERT INTO organizacion.almacenes (id_almacen, id_sede, nombre, tipo_almacen, estado)
OVERRIDING SYSTEM VALUE VALUES
(1, 1, 'Bodega Central de Almacenamiento Norte', 'principal', 'activo'),
(2, 2, 'Almacén de Venta / Exhibición Principal','venta',     'activo'),
(3, 3, 'Bodega Secundaria de Recepción',         'recepcion', 'activo'),
(4, 1, 'Punto de Venta Bogotá',                  'venta',     'activo'),
(5, 2, 'Almacén Principal Cali',                 'principal', 'activo'),
(6, 3, 'Punto de Venta Medellín',                'venta',     'activo'),
(7, 4, 'Almacén Principal Distribución',         'principal', 'activo'),
(8, 4, 'Bodega de Recepción Distribución',       'recepcion', 'activo');

SELECT setval(pg_get_serial_sequence('organizacion.sedes',     'id_sede'),    (SELECT max(id_sede)    FROM organizacion.sedes));
SELECT setval(pg_get_serial_sequence('organizacion.almacenes', 'id_almacen'), (SELECT max(id_almacen) FROM organizacion.almacenes));

COMMIT;
```

### 2.3 Vistas y consultas

**Conteos.** Muestra cuántas filas hay en `sedes` y en `almacenes`.

```sql
-- pruebas de consultas organziacion ---


-- Conteos
SELECT 'sedes' AS tabla, count(*) AS filas FROM organizacion.sedes
UNION ALL SELECT 'almacenes', count(*) FROM organizacion.almacenes;
```

**Almacenes por sede.** Lista cada sede con su tipo y los almacenes que le pertenecen (id, nombre y tipo de almacén).

```sql
-- Almacenes por sede
SELECT s.id_sede, s.nombre AS sede, s.tipo_sede, a.id_almacen, a.nombre AS almacen, a.tipo_almacen
FROM organizacion.sedes s JOIN organizacion.almacenes a ON a.id_sede = s.id_sede
ORDER BY s.id_sede, a.id_almacen;
```

**Almacenes usados por compras e inventarios.** Muestra id, nombre y ciudad de los almacenes 1, 2 y 3.

```sql
-- Almacenes que ya usan compras e inventarios 
SELECT a.id_almacen, a.nombre, s.ciudad
FROM organizacion.almacenes a JOIN organizacion.sedes s ON s.id_sede = a.id_sede
WHERE a.id_almacen IN (1, 2, 3) ORDER BY a.id_almacen;
```

**Pruebas de restricciones.** Ejecuta tres sentencias que violan a propósito la llave foránea, la restricción `UNIQUE` y un `CHECK`, y que deben terminar en error.

```sql
-- Pruebas de restricciones
INSERT INTO organizacion.almacenes (id_sede, nombre, tipo_almacen, estado) VALUES (99, 'X', 'venta', 'activo');       -- FK inexistente
INSERT INTO organizacion.sedes (nombre, ciudad, direccion, tipo_sede, estado) VALUES ('Sede Bogotá','Bogotá','x','comercial','activo'); -- UNIQUE
INSERT INTO organizacion.sedes (nombre, ciudad, direccion, tipo_sede, estado) VALUES ('Otra','Cali','x','mixta','activo');              -- CHECK
```

---

## 3. Compras (`compras`)

> Gobierna el ciclo de abastecimiento: proveedores, costos de referencia, órdenes de compra hacia los almacenes y registro histórico de recepciones parciales o totales.

### 3.1 Creación de tablas (DDL)

Se crea la base `compras_db` y seis tablas: `proveedores`, `ordenes_compra`, `recepciones_compra` y las tablas de rompimiento `producto_proveedor`, `detalle_orden_compra` y `detalle_recepcion`. Las relaciones internas usan llaves foráneas con nombre, mientras que `id_producto`, `id_almacen_destino` y `id_empleado_creador` son referencias lógicas a catalogo, organizacion e identidad. Se incluyen restricciones `CHECK` para estados, cantidades positivas y costos no negativos.

```sql
CREATE DATABASE compras_db;


-- CREACIÓN DE TABLAS

-- Proveedores
CREATE TABLE proveedores (
    id_proveedor 	INT 			GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    identificacion 	VARCHAR(20) 	NOT NULL CONSTRAINT id_unico UNIQUE,
    razon_social 	VARCHAR(100) 	NOT NULL CONSTRAINT razon_unica UNIQUE,
    ciudad 			VARCHAR(50) 	NOT NULL,
    correo 			VARCHAR(100) 	NOT NULL,
    telefono 		VARCHAR(20) 	NOT NULL,
    estado			VARCHAR(10) 	NOT NULL DEFAULT 'activo' CHECK (estado IN ('activo', 'inactivo'))
);


-- Órdenes de compra
CREATE TABLE ordenes_compra (
    id_orden_compra 	INT 		GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_proveedor 		INT 		NOT null CONSTRAINT fk_orden_proveedor REFERENCES proveedores(id_proveedor),
    id_almacen_destino 	INT 		NOT NULL,     -- Referencia lógica a organizacion_db (almacén de recepción)
    id_empleado_creador INT 		NOT NULL, 	    -- Referencia lógica a identidad_db (comprador)
    fecha_orden 		TIMESTAMP 	NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_estimada 		DATE 		NOT NULL,
    estado 				VARCHAR(20) NOT NULL DEFAULT 'pendiente'
        CHECK (estado IN (
            'pendiente',
            'recibida_parcial',
            'completada',
            'cancelada'
        ))
);


-- Recepciones de compra
CREATE TABLE recepciones_compra (
    id_recepcion 	INT 		GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_orden_compra INT 		NOT null CONSTRAINT fk_recepcion_orden REFERENCES ordenes_compra(id_orden_compra),
    fecha_recepcion TIMESTAMP 	NOT NULL DEFAULT CURRENT_TIMESTAMP,
    estado 			VARCHAR(20) NOT NULL DEFAULT 'procesada'
        CHECK (estado IN ('procesada', 'anulada'))
);


-- Tabla de rompimiento: producto_proveedor
CREATE TABLE producto_proveedor (
    id_producto 		INT NOT NULL, -- Referencia lógica a catalogo_db
    id_proveedor 		INT NOT null 	CONSTRAINT fk_prodprov_proveedor REFERENCES proveedores(id_proveedor),
    costo_referencia 	NUMERIC(12, 2) 	NOT null 	CHECK (costo_referencia >= 0),
    plazo_entrega_dias 	INT 			NOT null 	CHECK (plazo_entrega_dias >= 0),
    estado 				VARCHAR(10) 	NOT NULL 	DEFAULT 'activo' 	CHECK (estado IN ('activo', 'inactivo')),
    PRIMARY KEY (id_producto, id_proveedor)
);


-- Tabla de rompimiento: detalle_orden_compra
CREATE TABLE detalle_orden_compra (
    id_orden_compra 	INT 		NOT null	CONSTRAINT fk_detalleord_orden	 REFERENCES ordenes_compra(id_orden_compra),
    id_producto 		INT 		NOT NULL, 	-- Referencia lógica a catalogo_db
    cantidad_solicitada INT 		NOT null 	CHECK (cantidad_solicitada > 0),
    costo_unitario NUMERIC(12, 2) 	NOT null	CHECK (costo_unitario >= 0),
    PRIMARY KEY (id_orden_compra, id_producto)
);


-- Tabla de rompimiento: detalle_recepcion
CREATE TABLE detalle_recepcion (
    id_recepcion 		INT 	NOT null	CONSTRAINT fk_detallerec_recepcion	REFERENCES recepciones_compra(id_recepcion),
    id_producto 		INT 	NOT NULL, 	 -- Referencia lógica a catalogo_db
    cantidad_recibida 	INT 	NOT null	CHECK (cantidad_recibida > 0),
    PRIMARY KEY (id_recepcion, id_producto)
);
```

### 3.2 Inserción de datos (DML)

Se insertan 4 proveedores, 5 relaciones producto–proveedor con costo y plazo de entrega, 4 órdenes de compra en distintos estados (completada, recibida parcial, pendiente y cancelada) con sus detalles, 2 recepciones y 3 detalles de recepción. La orden 2 se recibe de forma parcial (120 de 200 unidades) para ilustrar el seguimiento del cumplimiento, y los id de producto, almacén y empleado coinciden con los demás microservicios.

```sql
--------- inserción de data de prueba ----


-- Proveedores
INSERT INTO proveedores (
    identificacion,
    razon_social,
    ciudad,
    correo,
    telefono,
    estado
)
VALUES
    ('900123456-1', 'Distribuidora Tech Colombia S.A.S.', 'Bogotá', 'contacto@techcolombia.com', '6013112233', 'activo'),
    ('800987654-2', 'Comercializadora de Bebidas del Valle S.A.', 'Cali', 'ventas@bebidasdelvalle.co', '6025554433', 'activo'),
    ('890555444-3', 'Suministros Industriales del Caribe Ltda.', 'Barranquilla', 'servicio@suministroscaribe.com', '6053778899', 'activo'),
    ('901222333-4', 'Textiles y Moda Nacional S.A.S.', 'Medellín', 'comercial@textilesmoda.com', '6044441122', 'inactivo');


-- Producto_proveedor
-- Relaciona los productos del catálogo con sus costos de compra y tiempos de entrega
INSERT INTO producto_proveedor (
    id_producto,
    id_proveedor,
    costo_referencia,
    plazo_entrega_dias,
    estado
)
VALUES
    (101, 1, 120000.00, 3, 'activo'),   -- Producto 101 proveído por Tech Colombia
    (102, 1, 450000.00, 5, 'activo'),   -- Producto 102 proveído por Tech Colombia
    (103, 2, 3500.00, 2, 'activo'),     -- Producto 103 proveído por Bebidas del Valle
    (104, 3, 25000.00, 7, 'activo'),    -- Producto 104 proveído por Suministros del Caribe
    (105, 4, 85000.00, 10, 'inactivo'); -- Producto 105 proveído por Textiles Nacional


-- Órdenes de compra
-- id_almacen_destino refiere a organizacion_db | id_empleado_creador refiere a identidad_db
INSERT INTO ordenes_compra (
    id_proveedor,
    id_almacen_destino,
    id_empleado_creador,
    fecha_orden,
    fecha_estimada,
    estado
)
VALUES
    (1, 1, 10, '2026-10-01 09:00:00', '2026-10-05', 'completada'),       -- Orden 1
    (2, 2, 11, '2026-10-10 14:30:00', '2026-10-13', 'recibida_parcial'), -- Orden 2
    (3, 1, 10, '2026-11-01 10:15:00', '2026-11-08', 'pendiente'),       -- Orden 3
    (4, 3, 11, '2026-11-02 11:00:00', '2026-11-12', 'cancelada');       -- Orden 4


-- Detalle_orden_compra
INSERT INTO detalle_orden_compra (
    id_orden_compra,
    id_producto,
    cantidad_solicitada,
    costo_unitario
)
VALUES
    (1, 101, 50, 120000.00), -- Orden 1 pide 50 unidades de Prod 101
    (1, 102, 30, 450000.00), -- Orden 1 pide 30 unidades de Prod 102
    (2, 103, 200, 3500.00),  -- Orden 2 pide 200 unidades de Prod 103
    (3, 104, 100, 25000.00), -- Orden 3 pide 100 unidades de Prod 104
    (4, 105, 15, 85000.00);  -- Orden 4 pide 15 unidades de Prod 105


-- Recepciones_compra
INSERT INTO recepciones_compra (
    id_orden_compra,
    fecha_recepcion,
    estado
)
VALUES
    (1, '2026-10-04 16:20:00', 'procesada'), -- Recepción 1 para Orden 1 (Completada)
    (2, '2026-10-12 11:10:00', 'procesada'); -- Recepción 2 para Orden 2 (Parcial)


-- Detalle_recepcion
INSERT INTO detalle_recepcion (
    id_recepcion,
    id_producto,
    cantidad_recibida
)
VALUES
    (1, 101, 50), -- Recepción 1 recibe completas las 50 un. de Prod 101
    (1, 102, 30), -- Recepción 1 recibe completas las 30 un. de Prod 102
    (2, 103, 120); -- Recepción 2 recibe solo 120 de las 200 un. de Prod 103 (Quedan 80 pendientes)
```

### 3.3 Vistas y consultas

**`v_resumen_cumplimiento_ordenes`.** Muestra, por cada orden de compra, el proveedor, las unidades y el valor solicitados, las unidades recibidas en recepciones procesadas y el porcentaje de cumplimiento.

```sql
--- vistas de prueba --- compras


--  v_resumen_cumplimiento_ordenes
CREATE OR REPLACE VIEW v_resumen_cumplimiento_ordenes AS
SELECT
    oc.id_orden_compra,
    oc.fecha_orden,
    oc.fecha_estimada,
    oc.estado AS estado_orden,
    p.id_proveedor,
    p.razon_social AS proveedor,
    p.ciudad AS ciudad_proveedor,
    oc.id_almacen_destino,
    COALESCE(SUM(doc.cantidad_solicitada), 0) AS total_unidades_solicitadas,
    COALESCE(SUM(doc.cantidad_solicitada * doc.costo_unitario), 0.00) AS valor_total_orden,
    COALESCE(SUM(dr.cantidad_recibida), 0) AS total_unidades_recibidas,
    ROUND(
        CASE
            WHEN SUM(doc.cantidad_solicitada) > 0
                THEN (
                    COALESCE(SUM(dr.cantidad_recibida), 0)::NUMERIC
                    / SUM(doc.cantidad_solicitada)::NUMERIC
                ) * 100.0
            ELSE 0.00
        END,
        2
    ) AS porcentaje_cumplimiento
FROM ordenes_compra oc
JOIN proveedores p
    ON oc.id_proveedor = p.id_proveedor
LEFT JOIN detalle_orden_compra doc
    ON oc.id_orden_compra = doc.id_orden_compra
LEFT JOIN recepciones_compra rc
    ON oc.id_orden_compra = rc.id_orden_compra
    AND rc.estado = 'procesada'
LEFT JOIN detalle_recepcion dr
    ON rc.id_recepcion = dr.id_recepcion
    AND doc.id_producto = dr.id_producto
GROUP BY
    oc.id_orden_compra,
    oc.fecha_orden,
    oc.fecha_estimada,
    oc.estado,
    p.id_proveedor,
    p.razon_social,
    p.ciudad,
    oc.id_almacen_destino;
```

**`v_catalogo_costos_proveedores`.** Muestra, para los proveedores activos, los productos que ofrecen con su costo de referencia, plazo de entrega, estado de la oferta y el total de órdenes históricas.

```sql
-- v_catalogo_costos_proveedores
CREATE OR REPLACE VIEW v_catalogo_costos_proveedores AS
SELECT
    p.id_proveedor,
    p.identificacion,
    p.razon_social,
    p.ciudad,
    pp.id_producto,
    pp.costo_referencia,
    pp.plazo_entrega_dias,
    pp.estado AS estado_oferta_producto,
    COUNT(DISTINCT oc.id_orden_compra) AS total_ordenes_historicas
FROM proveedores p
JOIN producto_proveedor pp
    ON p.id_proveedor = pp.id_proveedor
LEFT JOIN ordenes_compra oc
    ON p.id_proveedor = oc.id_proveedor
WHERE p.estado = 'activo'
GROUP BY
    p.id_proveedor,
    p.identificacion,
    p.razon_social,
    p.ciudad,
    pp.id_producto,
    pp.costo_referencia,
    pp.plazo_entrega_dias,
    pp.estado;
```

---

## 4. Inventarios (`inventarios`)

> Controla la existencia física por almacén y sede, el stock mínimo y el movimiento de mercancía entre almacenes mediante transferencias.

### 4.1 Creación de tablas (DDL)

Se crean tres tablas: `inventarios`, con la existencia actual y el stock mínimo por almacén y producto (única por pareja almacén–producto), `transferencias`, que registra los movimientos entre almacenes con sus fechas de solicitud, despacho y recepción, y `detalle_transferencia`, con los productos trasladados. Las restricciones `CHECK` impiden existencias negativas, cantidades no positivas y transferencias con el mismo almacén de origen y destino.

```sql
-- 1. INVENTARIOS (Existencias de productos por almacén)
CREATE TABLE inventarios (
    id_almacen	      	INT,				-- Referencia lógica a catalogo_db
    id_producto         INT 		NOT NULL,		-- Referencia lógica a catalogo_db
    id_sede				INT 		not null,		-- Referencia lógica a catalogo_db
    existencia_actual   INT 		NOT NULL DEFAULT 0	 CONSTRAINT chk_existencia_no_negativa CHECK (existencia_actual >= 0),
    stock_minimo        INT 		NOT NULL DEFAULT 10	CONSTRAINT chk_stock_min_no_negativo CHECK (stock_minimo >= 0),
    fecha_actualizacion TIMESTAMP 	NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uk_almacen_producto UNIQUE (id_almacen, id_producto)
);


-- 2. TRANSFERENCIAS (Movimientos de stock entre sedes/almacenes)
CREATE TABLE transferencias (
    id_transferencia        INT 		GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_almacen_origen       INT 		NOT NULL,	-- Referencia lógica a organizacion_db
    id_almacen_destino      INT 		NOT NULL,	-- Referencia lógica a organizacion_db
    fecha_solicitud         TIMESTAMP 	NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_despacho          TIMESTAMP,
    fecha_recepcion         TIMESTAMP,
    estado                  VARCHAR(20) NOT NULL DEFAULT 'solicitada'
        CHECK (estado IN ('solicitada', 'despachada', 'completada', 'cancelada')),
    CONSTRAINT chk_almacenes_diferentes
        CHECK (id_almacen_origen <> id_almacen_destino)
);


-- 3. DETALLE_TRANSFERENCIA (Productos trasladados en cada transferencia)
CREATE TABLE detalle_transferencia (
    id_transferencia 	INT 	NOT null	CONSTRAINT fk_dettransf_transferencia	REFERENCES transferencias(id_transferencia)	ON DELETE CASCADE,
    id_producto      	INT 	NOT NULL,	-- Referencia lógica a catalogo_db
    cantidad_enviada 	INT 	NOT null	CONSTRAINT chk_cant_enviada_pos CHECK (cantidad_enviada > 0),
    cantidad_recibida 	INT	CONSTRAINT chk_cant_recibida_valida CHECK (cantidad_recibida >= 0),
    PRIMARY KEY (id_transferencia, id_producto)
);
```

### 4.2 Inserción de datos (DML)

Se insertan 5 registros de inventario para los productos 101 a 105 en los almacenes 1 a 3, 3 transferencias en distintos estados (completada, despachada y solicitada) y 4 líneas de detalle. El producto 104 queda con cero existencias en el almacén 3 para activar la alerta de reabastecimiento, y las cantidades recibidas son `NULL` mientras la mercancía sigue en tránsito o solicitada.

```sql
-- =============================================================================
-- SCRIPT DE POBLAMIENTO DE DATOS DE PRUEBA: Módulo Inventarios y Transferencias
-- Base de Datos: inventarios_db (Servidor Azure PostgreSQL)
-- =============================================================================


-- Inventarios
-- Relaciona el stock físico de productos (101-105) en los almacenes (1-3)
INSERT INTO inventarios (
    id_almacen,
    id_producto,
    id_sede,
    existencia_actual,
    stock_minimo,
    fecha_actualizacion
)
VALUES
    (1, 101, 1, 50, 10, '2026-10-04 16:30:00'), -- Almacén 1 (Bogotá) tiene 50 un. de Prod 101 (Teclado)
    (1, 102, 1, 30, 5, '2026-10-04 16:30:00'),  -- Almacén 1 (Bogotá) tiene 30 un. de Prod 102 (Monitor)
    (2, 103, 2, 120, 20, '2026-10-12 11:15:00'), -- Almacén 2 (Cali) tiene 120 un. de Prod 103 (Bebidas)
    (3, 104, 3, 0, 15, '2026-11-01 08:00:00'),  -- Almacén 3 (Medellín) en 0 stock de Prod 104 (ALERTA REABASTECIMIENTO)
    (1, 105, 1, 15, 5, '2026-11-02 12:00:00'); -- Almacén 1 (Bogotá) tiene 15 un. de Prod 105 (Uniforme)


-- Transferencias
INSERT INTO transferencias (
    id_almacen_origen,
    id_almacen_destino,
    fecha_solicitud,
    fecha_despacho,
    fecha_recepcion,
    estado
)
VALUES
    (1, 2, '2026-11-05 10:00:00', '2026-11-05 14:00:00', '2026-11-06 09:30:00', 'completada'), -- Transferencia 1
    (1, 3, '2026-11-09 11:00:00', '2026-11-09 16:00:00', NULL, 'despachada'),                  -- Transferencia 2 (en tránsito)
    (2, 1, '2026-11-10 08:30:00', NULL, NULL, 'solicitada');                                  -- Transferencia 3 (pendiente)


-- Detalle_transferencia
INSERT INTO detalle_transferencia (
    id_transferencia,
    id_producto,
    cantidad_enviada,
    cantidad_recibida
)
VALUES
    (1, 101, 10, 10),  -- Transf 1: Se enviaron 10 un. de Prod 101 de Bogotá a Cali (Recibidas completas)
    (1, 102, 5, 5),    -- Transf 1: Se enviaron 5 un. de Prod 102 de Bogotá a Cali (Recibidas completas)
    (2, 104, 20, NULL),-- Transf 2: Se enviaron 20 un. de Prod 104 a Medellín (Aún en camino)
    (3, 103, 30, NULL);-- Transf 3: Solicitadas 30 un. de Prod 103 de Cali a Bogotá
```

### 4.3 Vistas y consultas

**`v_alertas_reabastecimiento_almacen`.** Muestra los productos cuya existencia está en o por debajo del stock mínimo, con su déficit y un nivel de prioridad (crítica o alerta), ordenados de menor a mayor existencia.

```sql
---- Script vista de prueba --- inventarios


--  v_alertas_reabastecimiento_almacen
CREATE OR REPLACE VIEW v_alertas_reabastecimiento_almacen AS
SELECT
    i.id_almacen,
    i.id_producto,
    i.existencia_actual,
    i.stock_minimo,
    (i.stock_minimo - i.existencia_actual) AS unidades_deficit,
    CASE
        WHEN i.existencia_actual = 0
            THEN 'CRÍTICA - STOCK AGOTADO'
        WHEN i.existencia_actual <= i.stock_minimo
            THEN 'ALERTA - REABASTECER'
        ELSE 'NORMAL - STOCK ADECUADO'
    END AS nivel_prioridad_alerta,
    i.fecha_actualizacion
FROM inventarios i
WHERE i.existencia_actual <= i.stock_minimo
ORDER BY
    i.existencia_actual ASC,
    i.stock_minimo DESC;
```

**`v_balance_transferencias_bodegas`.** Muestra, por cada transferencia, su origen, destino, estado, variedad de productos, unidades enviadas y recibidas, y la discrepancia entre ambas.

```sql
--  v_balance_transferencias_bodegas
CREATE OR REPLACE VIEW v_balance_transferencias_bodegas AS
SELECT
    t.id_transferencia,
    t.id_almacen_origen,
    t.id_almacen_destino,
    t.fecha_solicitud,
    t.fecha_despacho,
    t.fecha_recepcion,
    t.estado AS estado_transferencia,
    COUNT(dt.id_producto) AS variedad_productos_trasladados,
    COALESCE(SUM(dt.cantidad_enviada), 0) AS total_unidades_enviadas,
    COALESCE(SUM(dt.cantidad_recibida), 0) AS total_unidades_recibidas,
    (
        COALESCE(SUM(dt.cantidad_enviada), 0)
        - COALESCE(SUM(dt.cantidad_recibida), 0)
    ) AS discrepancia_unidades
FROM transferencias t
LEFT JOIN detalle_transferencia dt
    ON t.id_transferencia = dt.id_transferencia
GROUP BY
    t.id_transferencia,
    t.id_almacen_origen,
    t.id_almacen_destino,
    t.fecha_solicitud,
    t.fecha_despacho,
    t.fecha_recepcion,
    t.estado;
```

---

## 5. Ventas (`ventas`)

> Maneja el ciclo comercial orientado al cliente: clientes, pedidos de venta, detalle de cada pedido, pagos parciales o totales y devoluciones.

### 5.1 Creación de tablas (DDL)

Se crean seis tablas: `clientes`, `pedidos_venta`, `detalle_pedido`, `pagos`, `devoluciones` y `detalle_devolucion`. Los pedidos referencian a un cliente mediante llave foránea y los detalles se eliminan en cascada, mientras que sede, almacén, empleado y producto son referencias lógicas a otros microservicios. Las restricciones `CHECK` controlan estados, medios de pago, cantidades positivas y valores no negativos.

```sql
-- creacion de tablas ventas_db ---


-- 1. CLIENTES (Tabla Maestra Independiente)
CREATE TABLE clientes (
    id_cliente      INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tipo_documento  VARCHAR(5) NOT NULL,
    num_documento   VARCHAR(20) NOT NULL
        CONSTRAINT uq_cliente_num_doc UNIQUE,
    nombre_completo VARCHAR(120) NOT NULL,
    correo          VARCHAR(100) NOT NULL,
    telefono        VARCHAR(20) NOT NULL,
    estado          VARCHAR(10) NOT NULL DEFAULT 'activo'
        CHECK (estado IN ('activo', 'inactivo'))
);


-- 2. PEDIDOS DE VENTA (Sede / Almacén / Empleado son FKL)
CREATE TABLE pedidos_venta (
    id_pedido       INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_sede         INT NOT NULL,
    -- FKL a organizacion_db.sedes
    id_almacen      INT NOT NULL,
    -- FKL a organizacion_db.almacenes
    id_cliente      INT NOT NULL
        CONSTRAINT fk_pedido_cliente REFERENCES clientes(id_cliente),
    id_empleado     INT NOT NULL,
    -- FKL a identidad_db.empleados
    fecha_pedido    DATE NOT NULL DEFAULT CURRENT_DATE,
    estado          VARCHAR(15) NOT NULL DEFAULT 'pendiente'
        CHECK (estado IN ('pendiente', 'completado', 'cancelado', 'devolucion')),
    total_registrado NUMERIC(14,2) NOT NULL DEFAULT 0.00
        CHECK (total_registrado >= 0)
);


-- 3. DETALLE DE PEDIDO
CREATE TABLE detalle_pedido (
    id_pedido       INT NOT NULL
        CONSTRAINT fk_detpedido_pedido
        REFERENCES pedidos_venta(id_pedido)
        ON DELETE CASCADE,
    id_producto     INT NOT NULL,
    -- FKL a catalogo_db.productos
    cantidad        INT NOT NULL CHECK (cantidad > 0),
    precio_unitario NUMERIC(12,2) NOT NULL CHECK (precio_unitario >= 0),
    PRIMARY KEY (id_pedido, id_producto)
);


-- 4. PAGOS
CREATE TABLE pagos (
    id_pago     INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_pedido   INT NOT NULL
        CONSTRAINT fk_pago_pedido REFERENCES pedidos_venta(id_pedido),
    fecha_pago  DATE NOT NULL DEFAULT CURRENT_DATE,
    valor       NUMERIC(14,2) NOT NULL CHECK (valor > 0),
    medio_pago  VARCHAR(20) NOT NULL
        CHECK (medio_pago IN ('efectivo', 'tarjeta_credito', 'tarjeta_debito', 'transferencia')),
    estado      VARCHAR(15) NOT NULL DEFAULT 'aprobado'
        CHECK (estado IN ('aprobado', 'rechazado', 'anulado'))
);


-- 5. DEVOLUCIONES
CREATE TABLE devoluciones (
    id_devolucion   INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_pedido       INT NOT NULL
        CONSTRAINT fk_devolucion_pedido REFERENCES pedidos_venta(id_pedido),
    fecha_solicitud DATE NOT NULL DEFAULT CURRENT_DATE,
    motivo          VARCHAR(200) NOT NULL,
    estado          VARCHAR(15) NOT NULL DEFAULT 'pendiente'
        CHECK (estado IN ('pendiente', 'aprobada', 'rechazada'))
);


-- 6. DETALLE DE DEVOLUCION
CREATE TABLE detalle_devolucion (
    id_devolucion       INT NOT NULL
        CONSTRAINT fk_detdev_devolucion
        REFERENCES devoluciones(id_devolucion)
        ON DELETE CASCADE,
    id_producto         INT NOT NULL,
    -- FKL a catalogo_db.productos
    cantidad            INT NOT NULL CHECK (cantidad > 0),
    condicion_producto  VARCHAR(20) NOT NULL
        CHECK (condicion_producto IN ('buen_estado', 'defectuoso', 'empaque_abierto')),
    PRIMARY KEY (id_devolucion, id_producto)
);
```

### 5.2 Inserción de datos (DML)

Se insertan 4 clientes, 4 pedidos en distintos estados (completado, devolución y pendiente) con sus detalles, 4 pagos (uno de ellos dividido en dos abonos), una devolución aprobada y su detalle. El pedido 3 corresponde a la devolución de un teclado defectuoso, y los id de sede, almacén, empleado y producto coinciden con los datos de los otros microservicios.

```sql
-- agregación de datos a ventas ---
-- =============================================================================
-- SCRIPT DE POBLAMIENTO DE DATOS DE PRUEBA: Módulo Ventas y Pagos
-- Base de Datos: ventas_db
-- =============================================================================


-- Clientes
INSERT INTO clientes (
    tipo_documento,
    num_documento,
    nombre_completo,
    correo,
    telefono,
    estado
)
VALUES
    ('CC', '1018222333', 'Juan Pablo Pérez Gómez', 'juan.perez@email.com', '3101234567', 'activo'),
    ('CC', '1020444555', 'María Fernanda Suárez', 'maria.suarez@email.com', '3159876543', 'activo'),
    ('NIT', '901555666-8', 'Inversiones y Construcciones Capital S.A.S.', 'compras@inversionescapital.co', '6017890123', 'activo'),
    ('CE', 'E888999', 'John Alexander Smith', 'john.smith@email.com', '3204445566', 'inactivo');


-- Pedidos_venta
-- id_sede e id_almacen refieren a organizacion_db | id_empleado refiere a identidad_db
INSERT INTO pedidos_venta (
    id_sede,
    id_almacen,
    id_cliente,
    id_empleado,
    fecha_pedido,
    estado,
    total_registrado
)
VALUES
    (1, 1, 1, 10, '2026-10-15', 'completado', 1590000.00), -- Pedido 1 (Sede Bogotá, Vendedor 10)
    (2, 2, 2, 11, '2026-10-20', 'completado', 350000.00),  -- Pedido 2 (Sede Cali, Vendedora 11)
    (1, 1, 3, 10, '2026-11-03', 'devolucion', 600000.00),  -- Pedido 3 (Sede Bogotá, Vendedor 10)
    (3, 3, 4, 11, '2026-11-08', 'pendiente', 180000.00);   -- Pedido 4 (Sede Medellín, Vendedora 11)


-- Detalle_pedido
-- id_producto refiere a catalogo_db
INSERT INTO detalle_pedido (
    id_pedido,
    id_producto,
    cantidad,
    precio_unitario
)
VALUES
    (1, 101, 2, 170000.00),  -- Pedido 1: 2 Teclados Mecánicos
    (1, 102, 1, 1250000.00), -- Pedido 1: 1 Monitor Gamer 27"
    (2, 103, 100, 3500.00),  -- Pedido 2: 100 Bebidas Energizantes
    (3, 101, 3, 200000.00),  -- Pedido 3: 3 Teclados Mecánicos
    (4, 104, 5, 36000.00);   -- Pedido 4: 5 Kits de Limpieza


-- Pagos
INSERT INTO pagos (
    id_pedido,
    fecha_pago,
    valor,
    medio_pago,
    estado
)
VALUES
    (1, '2026-10-15', 1590000.00, 'tarjeta_credito', 'aprobado'), -- Pago completo Pedido 1
    (2, '2026-10-20', 200000.00, 'efectivo', 'aprobado'),         -- Pago parcial 1 Pedido 2
    (2, '2026-10-21', 150000.00, 'transferencia', 'aprobado'),   -- Pago parcial 2 Pedido 2 (Completa saldo)
    (3, '2026-11-03', 600000.00, 'tarjeta_debito', 'aprobado');  -- Pago completo Pedido 3


-- Devoluciones
INSERT INTO devoluciones (
    id_pedido,
    fecha_solicitud,
    motivo,
    estado
)
VALUES
    (3, '2026-11-05', 'Producto presentó falla eléctrica de fábrica en teclado', 'aprobada');


-- Detalle_devolucion
-- id_producto refiere a catalogo_db
INSERT INTO detalle_devolucion (
    id_devolucion,
    id_producto,
    cantidad,
    condicion_producto
)
VALUES
    (1, 101, 1, 'defectuoso'); -- Devolución 1: 1 unidad del Prod 101
```

### 5.3 Vistas y consultas

**`v_cartera_y_saldo_pedidos`.** Muestra, por cada pedido, el cliente, el valor total, lo recaudado con pagos aprobados, el saldo pendiente y el estado de cartera (pagado total, pago parcial o pendiente de pago).

```sql
 --- Vistas de prueba para ventas ----
    -- =============================================================================
-- VISTAS: Microservicio de Ventas y Pagos
-- =============================================================================


-- Vista 3.1: v_cartera_y_saldo_pedidos
CREATE OR REPLACE VIEW v_cartera_y_saldo_pedidos AS
SELECT
    pv.id_pedido,
    pv.fecha_pedido,
    pv.id_sede,
    pv.id_almacen,
    pv.id_empleado AS id_vendedor,
    c.id_cliente,
    c.tipo_documento || '-' || c.num_documento AS documento_cliente,
    c.nombre_completo AS cliente,
    pv.total_registrado AS valor_total_pedido,
    COALESCE(
        SUM(CASE WHEN p.estado = 'aprobado' THEN p.valor ELSE 0 END),
        0.00
    ) AS total_recaudado,
    (
        pv.total_registrado
        - COALESCE(
            SUM(CASE WHEN p.estado = 'aprobado' THEN p.valor ELSE 0 END),
            0.00
        )
    ) AS saldo_pendiente,
    CASE
        WHEN COALESCE(
            SUM(CASE WHEN p.estado = 'aprobado' THEN p.valor ELSE 0 END),
            0.00
        ) >= pv.total_registrado
            THEN 'PAGADO TOTAL'
        WHEN COALESCE(
            SUM(CASE WHEN p.estado = 'aprobado' THEN p.valor ELSE 0 END),
            0.00
        ) > 0
            THEN 'PAGO PARCIAL'
        ELSE 'PENDIENTE DE PAGO'
    END AS estado_cartera,
    pv.estado AS estado_pedido
FROM pedidos_venta pv
JOIN clientes c
    ON pv.id_cliente = c.id_cliente
LEFT JOIN pagos p
    ON pv.id_pedido = p.id_pedido
GROUP BY
    pv.id_pedido,
    pv.fecha_pedido,
    pv.id_sede,
    pv.id_almacen,
    pv.id_empleado,
    c.id_cliente,
    c.tipo_documento,
    c.num_documento,
    c.nombre_completo,
    pv.total_registrado,
    pv.estado;
```

**`v_devoluciones_impacto_ventas`.** Muestra cada producto devuelto con su devolución, pedido y cliente, la condición del producto y el impacto monetario calculado con el precio unitario del pedido.

```sql
-- Vista 3.2: v_devoluciones_impacto_ventas
CREATE OR REPLACE VIEW v_devoluciones_impacto_ventas AS
SELECT
    d.id_devolucion,
    d.fecha_solicitud,
    d.estado AS estado_devolucion,
    d.motivo,
    pv.id_pedido,
    pv.fecha_pedido,
    c.id_cliente,
    c.nombre_completo AS cliente,
    dd.id_producto,
    dd.cantidad AS cantidad_devuelta,
    dd.condicion_producto,
    dp.precio_unitario,
    (dd.cantidad * dp.precio_unitario) AS impacto_monetario_devolucion
FROM devoluciones d
JOIN pedidos_venta pv
    ON d.id_pedido = pv.id_pedido
JOIN clientes c
    ON pv.id_cliente = c.id_cliente
JOIN detalle_devolucion dd
    ON d.id_devolucion = dd.id_devolucion
LEFT JOIN detalle_pedido dp
    ON pv.id_pedido = dp.id_pedido
    AND dd.id_producto = dp.id_producto;
```

---

## 6. Identidad (`identidad`)

> Actúa como módulo de seguridad y administración de personal: empleados, cuentas de usuario y registro centralizado de auditoría de accesos.

### 6.1 Creación de tablas (DDL)

Se crea el esquema `identidad` con tres tablas: `empleados`, con documento único y cargo, `usuarios`, con una única cuenta por empleado y su hash de contraseña, y `auditoria_accesos`, que registra por usuario la fecha, la acción y el objeto consultado. Los roles de base de datos no se almacenan como columna de `usuarios`: se crean con `CREATE ROLE` y se asignan con `GRANT` y `REVOKE`.

```sql
--- creacion de tablas identidad ---

CREATE SCHEMA IF NOT EXISTS identidad;

CREATE TABLE IF NOT EXISTS identidad.empleados (
    id_empleado     INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_sede         INTEGER      NOT NULL,
    num_documento   VARCHAR(20)  NOT NULL UNIQUE,
    nombre_completo VARCHAR(120) NOT NULL,
    cargo           VARCHAR(60)  NOT NULL,
    correo          VARCHAR(100),
    estado          VARCHAR(10)  NOT NULL CHECK (estado IN ('activo','inactivo'))
);

CREATE TABLE IF NOT EXISTS identidad.usuarios (
    id_usuario     INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_empleado    INTEGER      NOT NULL UNIQUE REFERENCES identidad.empleados (id_empleado),
    nombre_usuario VARCHAR(50)  NOT NULL UNIQUE,
    password_hash  VARCHAR(255) NOT NULL,
    estado         VARCHAR(10)  NOT NULL CHECK (estado IN ('activo','inactivo')),
    fecha_creacion TIMESTAMP    NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS identidad.auditoria_accesos (
    id_auditoria      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_usuario        INTEGER      NOT NULL REFERENCES identidad.usuarios (id_usuario),
    fecha_hora        TIMESTAMP    NOT NULL DEFAULT now(),
    accion            VARCHAR(30)  NOT NULL,
    objeto_consultado VARCHAR(120) NOT NULL
);
```

### 6.2 Inserción de datos (DML)

Se vacían las tablas y se insertan 20 empleados de las cuatro sedes, 18 cuentas de usuario cuyo hash se calcula con `sha256` (solo como ejemplo de prueba) y 40 eventos de auditoría entre julio y octubre de 2026. Dos empleados quedan sin cuenta de usuario; al final se sincronizan las secuencias de identidad y se confirma con `COMMIT`.

```sql
--- adición de datos identidad ---


TRUNCATE identidad.auditoria_accesos, identidad.usuarios, identidad.empleados RESTART IDENTITY;

-- ------------------------------ empleados ------------------------------
INSERT INTO identidad.empleados (id_empleado, id_sede, num_documento, nombre_completo, cargo, correo, estado)
OVERRIDING SYSTEM VALUE VALUES
(1,  4, '1020304001', 'Carlos Andrés Rojas Pineda',      'Administrador',                          'crojas@distribuidora.example',    'activo'),
(2,  3, '1020304002', 'María Fernanda Cárdenas Ruiz',    'Gerente General',                        'mcardenas@distribuidora.example', 'activo'),
(3,  3, '1020304003', 'Julián Esteban Moreno Salas',     'Auditor',                                'jmoreno@distribuidora.example',   'activo'),
(4,  1, '1020304004', 'Laura Sofía Peña Ortiz',          'Responsable de Inventario',              'lpena@distribuidora.example',     'activo'),
(5,  2, '1020304005', 'Andrés Felipe Gómez Cuesta',      'Responsable de Inventario',              'agomez@distribuidora.example',    'activo'),
(6,  3, '1020304006', 'Diana Carolina Vargas Mejía',     'Responsable de Inventario',              'dvargas@distribuidora.example',   'activo'),
(7,  4, '1020304007', 'Sergio Iván Ramírez Torres',      'Responsable de Inventario',              'sramirez@distribuidora.example',  'activo'),
(8,  4, '1020304008', 'Natalia Andrea Castro Londoño',   'Responsable de Compras',                 'ncastro@distribuidora.example',   'activo'),
(9,  3, '1020304009', 'Camilo José Herrera Bustos',      'Auxiliar de Logística',                  'cherrera@distribuidora.example',  'activo'),
(10, 1, '1020304010', 'Carlos Mendoza',                  'Responsable de Compras',                 'cmendoza@distribuidora.example',  'activo'),
(11, 1, '1020304011', 'Andrea López',                    'Auxiliar de Abastecimiento y Logística', 'alopez@distribuidora.example',    'activo'),
(12, 1, '1020304012', 'Paola Andrea Suárez Gil',         'Vendedor',                               'psuarez@distribuidora.example',   'activo'),
(13, 1, '1020304013', 'Daniel Alejandro Silva Rincón',   'Vendedor',                               NULL,                              'activo'),
(14, 1, '1020304014', 'Valentina Ospina Duque',          'Vendedor',                               'vospina@distribuidora.example',   'activo'),
(15, 2, '1020304015', 'Luis Fernando Quintero Mora',     'Vendedor',                               'lquintero@distribuidora.example', 'inactivo'),
(16, 2, '1020304016', 'Marcela Patricia León Vega',      'Vendedor',                               'mleon@distribuidora.example',     'activo'),
(17, 3, '1020304017', 'Ricardo Alonso Barrera Nieto',    'Vendedor',                               'rbarrera@distribuidora.example',  'activo'),
(18, 3, '1020304018', 'Angie Tatiana Pardo Cruz',        'Vendedor',                               'apardo@distribuidora.example',    'activo'),
(19, 3, '1020304019', 'Felipe Esteban Salazar Roa',      'Vendedor',                               NULL,                              'activo'),
(20, 4, '1020304020', 'Johana Milena Acosta Prieto',     'Vendedor',                               'jacosta@distribuidora.example',   'activo');

-- ------------------------------ usuarios -------------------------------
-- password_hash = SHA-256 de '<usuario>:prueba2026' (ejemplo; en un sistema real, bcrypt o argon2 con sal).
INSERT INTO identidad.usuarios (id_usuario, id_empleado, nombre_usuario, password_hash, estado, fecha_creacion)
OVERRIDING SYSTEM VALUE
SELECT v.id_usuario, v.id_empleado, v.nombre_usuario,
       encode(sha256(convert_to(v.nombre_usuario || ':prueba2026', 'UTF8')), 'hex'),
       v.estado, v.fecha_creacion
FROM (VALUES
 (1,  1,  'crojas',    'activo',   TIMESTAMP '2026-06-01 08:00'),
 (2,  2,  'mcardenas', 'activo',   TIMESTAMP '2026-06-01 08:10'),
 (3,  3,  'jmoreno',   'activo',   TIMESTAMP '2026-06-01 08:20'),
 (4,  4,  'lpena',     'activo',   TIMESTAMP '2026-06-02 09:00'),
 (5,  5,  'agomez',    'activo',   TIMESTAMP '2026-06-02 09:10'),
 (6,  6,  'dvargas',   'activo',   TIMESTAMP '2026-06-02 09:20'),
 (7,  7,  'sramirez',  'activo',   TIMESTAMP '2026-06-02 09:30'),
 (8,  8,  'ncastro',   'activo',   TIMESTAMP '2026-06-03 09:00'),
 (9,  9,  'cherrera',  'activo',   TIMESTAMP '2026-06-03 09:10'),
 (10, 10, 'cmendoza',  'activo',   TIMESTAMP '2026-06-05 10:00'),
 (11, 11, 'alopez',    'activo',   TIMESTAMP '2026-07-01 09:00'),
 (12, 12, 'psuarez',   'activo',   TIMESTAMP '2026-06-05 10:10'),
 (13, 14, 'vospina',   'activo',   TIMESTAMP '2026-06-18 11:00'),
 (14, 15, 'lquintero', 'inactivo', TIMESTAMP '2026-06-18 11:10'),
 (15, 16, 'mleon',     'activo',   TIMESTAMP '2026-06-18 11:20'),
 (16, 17, 'rbarrera',  'activo',   TIMESTAMP '2026-06-19 09:00'),
 (17, 18, 'apardo',    'activo',   TIMESTAMP '2026-06-19 09:10'),
 (18, 20, 'jacosta',   'activo',   TIMESTAMP '2026-09-01 08:05')
) AS v(id_usuario, id_empleado, nombre_usuario, estado, fecha_creacion);

-- ----------------------------- auditoría -------------------------------
-- 40 eventos entre el 1 de julio y el 30 de octubre de 2026, en orden cronológico.
INSERT INTO identidad.auditoria_accesos (id_usuario, fecha_hora, accion, objeto_consultado) VALUES
(1,  '2026-07-01 08:05', 'LOGIN',  'identidad.usuarios'),
(1,  '2026-07-01 08:20', 'INSERT', 'identidad.empleados'),
(2,  '2026-07-02 09:10', 'SELECT', 'reportes.vista_reporte_corporativo'),
(3,  '2026-07-03 10:30', 'SELECT', 'identidad.auditoria_accesos'),
(13, '2026-07-06 09:00', 'INSERT', 'ventas.sede_bogota_pedidos'),
(15, '2026-07-07 11:15', 'INSERT', 'ventas.sede_cali_pedidos'),
(16, '2026-07-08 14:40', 'INSERT', 'ventas.sede_medellin_pedidos'),
(4,  '2026-07-10 08:45', 'UPDATE', 'inventarios.sede_bogota_inventarios'),
(8,  '2026-07-12 10:00', 'INSERT', 'compras.ordenes_compra'),
(10, '2026-07-14 15:20', 'INSERT', 'compras.recepciones_compra'),
(2,  '2026-07-20 09:30', 'SELECT', 'reportes.vista_ventas_mensuales_por_sede'),
(5,  '2026-07-22 13:05', 'UPDATE', 'inventarios.sede_cali_inventarios'),
(12, '2026-07-25 16:10', 'INSERT', 'ventas.pagos'),
(7,  '2026-08-03 08:50', 'INSERT', 'inventarios.transferencias'),
(6,  '2026-08-05 12:25', 'UPDATE', 'inventarios.sede_medellin_inventarios'),
(3,  '2026-08-06 09:40', 'SELECT', 'reportes.vista_reporte_corporativo'),
(12, '2026-08-10 10:35', 'INSERT', 'ventas.sede_bogota_pedidos'),
(14, '2026-08-12 11:50', 'INSERT', 'ventas.sede_cali_pedidos'),
(1,  '2026-08-14 08:10', 'UPDATE', 'catalogo.productos'),
(15, '2026-08-18 15:45', 'INSERT', 'ventas.devoluciones'),
(2,  '2026-08-25 09:15', 'SELECT', 'reportes.vista_alertas_reabastecimiento'),
(8,  '2026-08-28 10:20', 'UPDATE', 'compras.ordenes_compra'),
(1,  '2026-08-31 17:00', 'UPDATE', 'identidad.usuarios'),
(1,  '2026-09-01 08:00', 'INSERT', 'identidad.usuarios'),
(17, '2026-09-02 14:00', 'INSERT', 'ventas.sede_medellin_pedidos'),
(4,  '2026-09-04 08:30', 'SELECT', 'reportes.vista_inventario_por_sede'),
(3,  '2026-09-08 11:00', 'SELECT', 'identidad.auditoria_accesos'),
(13, '2026-09-10 12:40', 'UPDATE', 'ventas.sede_bogota_pedidos'),
(11, '2026-09-15 09:25', 'INSERT', 'inventarios.transferencias'),
(15, '2026-09-22 16:30', 'INSERT', 'ventas.pagos'),
(18, '2026-09-25 10:05', 'INSERT', 'ventas.sede_distribucion_pedidos'),
(10, '2026-10-01 09:45', 'INSERT', 'compras.ordenes_compra'),
(5,  '2026-10-05 13:30', 'UPDATE', 'inventarios.sede_cali_inventarios'),
(2,  '2026-10-08 08:55', 'SELECT', 'reportes.vista_saldos_pendientes'),
(16, '2026-10-12 15:10', 'INSERT', 'ventas.pagos'),
(6,  '2026-10-14 10:50', 'SELECT', 'inventarios.sede_medellin_inventarios'),
(3,  '2026-10-20 09:20', 'SELECT', 'reportes.vista_reporte_corporativo'),
(13, '2026-10-22 11:35', 'INSERT', 'ventas.sede_bogota_pedidos'),
(8,  '2026-10-27 14:25', 'INSERT', 'compras.recepciones_compra'),
(1,  '2026-10-30 08:40', 'SELECT', 'identidad.auditoria_accesos');

SELECT setval(pg_get_serial_sequence('identidad.empleados', 'id_empleado'), (SELECT max(id_empleado) FROM identidad.empleados));
SELECT setval(pg_get_serial_sequence('identidad.usuarios',  'id_usuario'),  (SELECT max(id_usuario)  FROM identidad.usuarios));

COMMIT;
```

### 6.3 Vistas y consultas

**Conteos.** Muestra cuántas filas hay en `empleados`, `usuarios` y `auditoria_accesos`.

```sql
--- pruebas de consultas identidad ---


-- Conteos.
SELECT 'empleados' AS tabla, count(*) AS filas FROM identidad.empleados
UNION ALL SELECT 'usuarios', count(*) FROM identidad.usuarios
UNION ALL SELECT 'auditoria_accesos', count(*) FROM identidad.auditoria_accesos;
```

**Empleados usados por compras e inventarios.** Muestra id, nombre, cargo y sede de los empleados 10 y 11.

```sql
-- Empleados que ya usan compras e inventarios
SELECT id_empleado, nombre_completo, cargo, id_sede FROM identidad.empleados WHERE id_empleado IN (10, 11) ORDER BY id_empleado;
```

**Empleados por sede.** Cuenta cuántos empleados hay en cada sede.

```sql
-- Empleados por sede 

SELECT id_sede, count(*) AS empleados FROM identidad.empleados GROUP BY id_sede ORDER BY id_sede;
```

**Empleados por cargo.** Cuenta cuántos empleados hay por cada cargo.

```sql
-- Empleados por cargo.
SELECT cargo, count(*) FROM identidad.empleados GROUP BY cargo ORDER BY cargo;
```

**Empleados sin cuenta de usuario.** Lista los empleados que no tienen ninguna cuenta de usuario asociada.

```sql
-- Empleados sin cuenta de usuario
SELECT e.id_empleado, e.nombre_completo FROM identidad.empleados e
WHERE NOT EXISTS (SELECT 1 FROM identidad.usuarios u WHERE u.id_empleado = e.id_empleado) ORDER BY e.id_empleado;
```

**Auditoría.** Cuenta los eventos por tipo de acción y muestra la fecha del primer y del último evento registrado.

```sql
-- Auditoría. 
SELECT accion, count(*) FROM identidad.auditoria_accesos GROUP BY accion ORDER BY accion;
SELECT min(fecha_hora) AS primera, max(fecha_hora) AS ultima FROM identidad.auditoria_accesos;
```

**Pruebas de restricciones.** Ejecuta cuatro sentencias que violan a propósito las restricciones `UNIQUE`, la llave foránea y un `CHECK`, y que deben terminar en error.

```sql
-- Pruebas de restricciones 
INSERT INTO identidad.usuarios (id_empleado, nombre_usuario, password_hash, estado) VALUES (1, 'otro', 'x', 'activo');   -- UNIQUE (el empleado 1 ya tiene cuenta)
INSERT INTO identidad.usuarios (id_empleado, nombre_usuario, password_hash, estado) VALUES (999, 'fantasma', 'x', 'activo'); -- FK (empleado inexistente)
INSERT INTO identidad.empleados (id_sede, num_documento, nombre_completo, cargo, estado) VALUES (1, '1020304001', 'Repetido', 'Vendedor', 'activo'); -- UNIQUE (documento)
UPDATE identidad.empleados SET estado = 'despedido' WHERE id_empleado = 1;                                                -- CHECK IN (estado)
```
