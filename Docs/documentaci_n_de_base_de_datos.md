# scripts sql DDL y DML

- Erick Santiago Buitrago Peña - 20221020072
- Dairo Alejandro Nestiel Muñoz - 20231020025

## Contexto de Despliegue en Azure

Las bases de datos están cada una desplegada en un recurso "Azure Database for PostgreSQL flexible server" de Azure, ubicadas en un mismo grupo de recursos y configuradas con acceso público temporal para la ejecución de los scripts desde las máquinas locales y demostraciones. Sin embargo, posteriormente estas bases de datos únicamente se podrán accesar desde las APIs correspondientes a cada microservicio de manera interna y segura.

---

## 1. Catálogo

Gestiona la metadata maestra del producto: qué vende la empresa, cómo se clasifica y en qué unidad se mide.

Se definen las estructuras DDL para organizar la información de manera estructurada y normalizada.
Estas tablas permiten categorizar los productos y almacenar sus características principales con restricciones clave.
Se establecen llaves primarias, foráneas y restricciones de unicidad para mantener la integridad de los datos.

```sql
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

Se realiza la inserción masiva de datos iniciales para categorías y productos del inventario general.
Se utiliza la instrucción TRUNCATE con RESTART IDENTITY y sobreescritura de valores de sistema para control de IDs.
Estos registros inicializan el catálogo corporativo con diferentes líneas de productos y estados activos o inactivos.

```sql
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

Se ejecutan consultas de conteo, agrupación por categoría y filtrado de productos específicos.
Se muestran estadísticas de conteos totales, productos por categoría y productos inactivos.
Se incluyen pruebas de restricciones y validación de actualizaciones lógicas del catálogo.

```sql
-- Conteos
SELECT 'categorias' AS tabla, count(*) AS filas FROM catalogo.categorias
UNION ALL SELECT 'productos', count(*) FROM catalogo.productos
UNION ALL SELECT 'productos activos', count(*) FROM catalogo.productos WHERE estado = 'activo'
UNION ALL SELECT 'productos inactivos', count(*) FROM catalogo.productos WHERE estado = 'inactivo';

-- Productos por categoría.
SELECT c.id_categoria, c.nombre, count(p.id_producto) AS productos
FROM catalogo.categorias c LEFT JOIN catalogo.productos p ON p.id_categoria = c.id_categoria
GROUP BY c.id_categoria, c.nombre ORDER BY c.id_categoria;

-- Productos que ya usan compras e inventarios 
SELECT id_producto, sku, nombre, precio_lista FROM catalogo.productos
WHERE id_producto IN (101, 102, 103, 104, 105) ORDER BY id_producto;

-- Productos inactivos
SELECT id_producto, sku, nombre FROM catalogo.productos WHERE estado = 'inactivo' ORDER BY id_producto;

-- Pruebas de restricciones
INSERT INTO catalogo.productos (sku,nombre,id_categoria,unidad_medida,precio_lista,estado) VALUES ('GRA-ARR-500','Repetido',1,'unidad',2800,'activo');  -- UNIQUE (SKU duplicado)
INSERT INTO catalogo.productos (sku,nombre,id_categoria,unidad_medida,precio_lista,estado) VALUES ('T-NEG','Prueba',1,'unidad',-100,'activo');          -- CHECK (precio negativo)
INSERT INTO catalogo.productos (sku,nombre,id_categoria,unidad_medida,precio_lista,estado) VALUES ('T-FK','Prueba',999,'unidad',1000,'activo');         -- FK (categoría inexistente)
UPDATE catalogo.productos SET estado = 'borrado' WHERE id_producto = 1;                                                                                 -- CHECK IN (estado)

-- Eliminación lógica (en lugar de DELETE):
UPDATE catalogo.productos SET estado = 'inactivo' WHERE id_producto = 13;
```

---

## 2. Organización

Administra la infraestructura física y logística: la jerarquía de sedes comerciales, el centro de distribución y almacenes.

Se inicializa la base de datos y se diseñan las tablas relacionales para sedes y almacenes corporativos.
Se implementan restricciones de unicidad y verificación para asegurar tipos de sedes y bodegas válidos.
Se establecen llaves foráneas para relacionar directamente cada almacén con su sede correspondiente.

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

Se realiza la carga inicial de registros para las sedes comerciales y almacenes operativos del sistema.
Se limpian las tablas previas reiniciando las secuencias de identidad para mantener orden numérico consecutivo.
Los datos de prueba configuran sedes en Bogotá, Cali, Medellín y el centro de distribución en Barranquilla.

```sql
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
INSERT INTO producto_proveedor (
    id_producto,
    id_proveedor,
    costo_referencia,
    plazo_entrega_dias,
    estado
)
VALUES
    (101, 1, 120000.00, 3, 'activo'),
    (102, 1, 450000.00, 5, 'activo'),
    (103, 2, 3500.00, 2, 'activo'),
    (104, 3, 25000.00, 7, 'activo'),
    (105, 4, 85000.00, 10, 'inactivo');

-- Órdenes de compra
INSERT INTO ordenes_compra (
    id_proveedor,
    id_almacen_destino,
    id_empleado_creador,
    fecha_orden,
    fecha_estimada,
    estado
)
VALUES
    (1, 1, 10, '2026-10-01 09:00:00', '2026-10-05', 'completada'),
    (2, 2, 11, '2026-10-10 14:30:00', '2026-10-13', 'recibida_parcial'),
    (3, 1, 10, '2026-11-01 10:15:00', '2026-11-08', 'pendiente'),
    (4, 3, 11, '2026-11-02 11:00:00', '2026-11-12', 'cancelada');

-- Detalle_orden_compra
INSERT INTO detalle_orden_compra (
    id_orden_compra,
    id_producto,
    cantidad_solicitada,
    costo_unitario
)
VALUES
    (1, 101, 50, 120000.00),
    (1, 102, 30, 450000.00),
    (2, 103, 200, 3500.00),
    (3, 104, 100, 25000.00),
    (4, 105, 15, 85000.00);

-- Recepciones_compra
INSERT INTO recepciones_compra (
    id_orden_compra,
    fecha_recepcion,
    estado
)
VALUES
    (1, '2026-10-04 16:20:00', 'procesada'),
    (2, '2026-10-12 11:10:00', 'procesada');

-- Detalle_recepcion
INSERT INTO detalle_recepcion (
    id_recepcion,
    id_producto,
    cantidad_recibida
)
VALUES
    (1, 101, 50),
    (1, 102, 30),
    (2, 103, 120);
```

Se ejecutan consultas de conteo global, relación jerárquica entre sedes y almacenes, y validaciones de restricciones.
- Muestra el conteo total de registros de sedes y almacenes corporativos.
- Muestra el listado detallado de almacenes asociados a cada sede de la empresa.
- Muestra los almacenes específicos vinculados con los procesos de compras e inventarios.
- Valida las restricciones de integridad referencial y de dominio mediante inserciones erróneas de prueba.

```sql
-- Conteos
SELECT 'sedes' AS tabla, count(*) AS filas FROM organizacion.sedes
UNION ALL SELECT 'almacenes', count(*) FROM organizacion.almacenes;

-- Almacenes por sede
SELECT s.id_sede, s.nombre AS sede, s.tipo_sede, a.id_almacen, a.nombre AS almacen, a.tipo_almacen
FROM organizacion.sedes s JOIN organizacion.almacenes a ON a.id_sede = s.id_sede
ORDER BY s.id_sede, a.id_almacen;

-- Almacenes que ya usan compras e inventarios 
SELECT a.id_almacen, a.nombre, s.ciudad
FROM organizacion.almacenes a JOIN organizacion.sedes s ON s.id_sede = a.id_sede
WHERE a.id_almacen IN (1, 2, 3) ORDER BY a.id_almacen;

-- Pruebas de restricciones
INSERT INTO organizacion.almacenes (id_sede, nombre, tipo_almacen, estado) VALUES (99, 'X', 'venta', 'activo');       -- FK inexistente
INSERT INTO organizacion.sedes (nombre, ciudad, direccion, tipo_sede, estado) VALUES ('Sede Bogotá','Bogotá','x','comercial','activo'); -- UNIQUE
INSERT INTO organizacion.sedes (nombre, ciudad, direccion, tipo_sede, estado) VALUES ('Otra','Cali','x','mixta','activo');              -- CHECK
```

---

## 3. Compras

Gobierna el ciclo de abastecimiento: directorio de proveedores, costos de referencia, órdenes de compra y recepciones.

Se estructuran las tablas relacionales para el control de proveedores, órdenes de compra y recepciones de mercancía.
Se crean tablas de rompimiento y detalle para asociar productos con proveedores y gestionar cantidades solicitadas.
Se aplican restricciones de verificación en costos, plazos de entrega y estados de órdenes con dominios estrictos.

```sql
-- (Nota: la creación de base de datos se omitirá o mantendrá según el script original)
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
    id_almacen_destino 	INT 		NOT NULL,
    id_empleado_creador INT 		NOT NULL,
    fecha_orden 		TIMESTAMP 	NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_estimada 		DATE 		NOT NULL,
    estado 				VARCHAR(20) NOT NULL DEFAULT 'pendiente'
        CHECK (estado IN ('pendiente', 'recibida_parcial', 'completada', 'cancelada'))
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
    id_producto 		INT NOT NULL,
    id_proveedor 		INT NOT null 	CONSTRAINT fk_prodprov_proveedor REFERENCES proveedores(id_proveedor),
    costo_referencia 	NUMERIC(12, 2) 	NOT null 	CHECK (costo_referencia >= 0),
    plazo_entrega_dias 	INT 			NOT null 	CHECK (plazo_entrega_dias >= 0),
    estado 				VARCHAR(10) 	NOT NULL 	DEFAULT 'activo' 	CHECK (estado IN ('activo', 'inactivo')),
    PRIMARY KEY (id_producto, id_proveedor)
);

-- Tabla de rompimiento: detalle_orden_compra
CREATE TABLE detalle_orden_compra (
    id_orden_compra 	INT 		NOT null	CONSTRAINT fk_detalleord_orden	 REFERENCES ordenes_compra(id_orden_compra),
    id_producto 		INT 		NOT NULL,
    cantidad_solicitada INT 		NOT null 	CHECK (cantidad_solicitada > 0),
    costo_unitario NUMERIC(12, 2) 	NOT null	CHECK (costo_unitario >= 0),
    PRIMARY KEY (id_orden_compra, id_producto)
);

-- Tabla de rompimiento: detalle_recepcion
CREATE TABLE detalle_recepcion (
    id_recepcion 		INT 	NOT null	CONSTRAINT fk_detallerec_recepcion	REFERENCES recepciones_compra(id_recepcion),
    id_producto 		INT 	NOT NULL,
    cantidad_recibida 	INT 	NOT null	CHECK (cantidad_recibida > 0),
    PRIMARY KEY (id_recepcion, id_producto)
);
```

Se insertan registros de prueba correspondientes a proveedores registrados y sus ofertas de productos asociadas.
Se registran órdenes de compra y sus detalles con cantidades, costos unitarios y fechas estimadas de entrega.
Se agregan los registros de recepciones de mercancía parciales y totales vinculados al histórico de compras.

```sql
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
INSERT INTO producto_proveedor (
    id_producto,
    id_proveedor,
    costo_referencia,
    plazo_entrega_dias,
    estado
)
VALUES
    (101, 1, 120000.00, 3, 'activo'),
    (102, 1, 450000.00, 5, 'activo'),
    (103, 2, 3500.00, 2, 'activo'),
    (104, 3, 25000.00, 7, 'activo'),
    (105, 4, 85000.00, 10, 'inactivo');

-- Órdenes de compra
INSERT INTO ordenes_compra (
    id_proveedor,
    id_almacen_destino,
    id_empleado_creador,
    fecha_orden,
    fecha_estimada,
    estado
)
VALUES
    (1, 1, 10, '2026-10-01 09:00:00', '2026-10-05', 'completada'),
    (2, 2, 11, '2026-10-10 14:30:00', '2026-10-13', 'recibida_parcial'),
    (3, 1, 10, '2026-11-01 10:15:00', '2026-11-08', 'pendiente'),
    (4, 3, 11, '2026-11-02 11:00:00', '2026-11-12', 'cancelada');

-- Detalle_orden_compra
INSERT INTO detalle_orden_compra (
    id_orden_compra,
    id_producto,
    cantidad_solicitada,
    costo_unitario
)
VALUES
    (1, 101, 50, 120000.00),
    (1, 102, 30, 450000.00),
    (2, 103, 200, 3500.00),
    (3, 104, 100, 25000.00),
    (4, 105, 15, 85000.00);

-- Recepciones_compra
INSERT INTO recepciones_compra (
    id_orden_compra,
    fecha_recepcion,
    estado
)
VALUES
    (1, '2026-10-04 16:20:00', 'procesada'),
    (2, '2026-10-12 11:10:00', 'procesada');

-- Detalle_recepcion
INSERT INTO detalle_recepcion (
    id_recepcion,
    id_producto,
    cantidad_recibida
)
VALUES
    (1, 101, 50),
    (1, 102, 30),
    (2, 103, 120);
```

Se configuran vistas analíticas para el seguimiento de órdenes de compra y costos de proveedores activos.
- Muestra el resumen consolidado del cumplimiento de órdenes de compra y porcentajes recibidos.
- Muestra el catálogo de costos y plazos de entrega asociados a cada proveedor activo.

```sql
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

## 4. Inventarios

Controla la existencia física por almacén y sede, el stock mínimo y el movimiento de mercancía entre almacenes.

Se definen las tablas de inventario físico, transferencias entre bodegas y el detalle de los traslados.
Se incorporan restricciones de unicidad para evitar duplicidad de productos por almacén y control de existencia no negativa.
Se establece una validación para garantizar que los almacenes de origen y destino en transferencias sean diferentes.

```sql
-- 1. INVENTARIOS (Existencias de productos por almacén)
CREATE TABLE inventarios (
    id_almacen	      	INT,
    id_producto         INT 		NOT NULL,
    id_sede				INT 		not null,
    existencia_actual   INT 		NOT NULL DEFAULT 0	 CONSTRAINT chk_existencia_no_negativa CHECK (existencia_actual >= 0),
    stock_minimo        INT 		NOT NULL DEFAULT 10	CONSTRAINT chk_stock_min_no_negativo CHECK (stock_minimo >= 0),
    fecha_actualizacion TIMESTAMP 	NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uk_almacen_producto UNIQUE (id_almacen, id_producto)
);

-- 2. TRANSFERENCIAS (Movimientos de stock entre sedes/almacenes)
CREATE TABLE transferencias (
    id_transferencia        INT 		GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_almacen_origen       INT 		NOT NULL,
    id_almacen_destino      INT 		NOT NULL,
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
    id_producto      	INT 	NOT NULL,
    cantidad_enviada 	INT 	NOT null	CONSTRAINT chk_cant_enviada_pos CHECK (cantidad_enviada > 0),
    cantidad_recibida 	INT	CONSTRAINT chk_cant_recibida_valida CHECK (cantidad_recibida >= 0),
    PRIMARY KEY (id_transferencia, id_producto)
);
```

Se insertan datos iniciales para simular las existencias de productos en los diferentes almacenes logísticos.
Se registran transferencias de mercancía en diferentes estados como completada, despachada y solicitada.
Se completan los detalles de las transferencias especificando cantidades enviadas y recibidas por producto.

```sql
-- Inventarios
INSERT INTO inventarios (
    id_almacen,
    id_producto,
    id_sede,
    existencia_actual,
    stock_minimo,
    fecha_actualizacion
)
VALUES
    (1, 101, 1, 50, 10, '2026-10-04 16:30:00'),
    (1, 102, 1, 30, 5, '2026-10-04 16:30:00'),
    (2, 103, 2, 120, 20, '2026-10-12 11:15:00'),
    (3, 104, 3, 0, 15, '2026-11-01 08:00:00'),
    (1, 105, 1, 15, 5, '2026-11-02 12:00:00');

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
    (1, 2, '2026-11-05 10:00:00', '2026-11-05 14:00:00', '2026-11-06 09:30:00', 'completada'),
    (1, 3, '2026-11-09 11:00:00', '2026-11-09 16:00:00', NULL, 'despachada'),
    (2, 1, '2026-11-10 08:30:00', NULL, NULL, 'solicitada');

-- Detalle_transferencia
INSERT INTO detalle_transferencia (
    id_transferencia,
    id_producto,
    cantidad_enviada,
    cantidad_recibida
)
VALUES
    (1, 101, 10, 10),
    (1, 102, 5, 5),
    (2, 104, 20, NULL),
    (3, 103, 30, NULL);
```

Se implementan vistas de control de stock y seguimiento de transferencias entre bodegas.
- Muestra las alertas de reabastecimiento y déficit crítico de productos por almacén.
- Muestra el balance consolidado de transferencias de mercancía y discrepancias de unidades.

```sql
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

## 5. Ventas

Maneja el ciclo comercial orientado al cliente: clientes, pedidos de venta, detalle de cada pedido, pagos y devoluciones.

Se configuran las estructuras de bases de datos para clientes, pedidos, detalles, pagos y devoluciones.
Se establecen llaves foráneas e integridad referencial garantizando el vínculo con entidades de otros microservicios.
Se aplican restricciones de verificación de estados comerciales y montos monetarios válidos no negativos.

```sql
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

Se insertan datos iniciales de prueba para clientes, pedidos de venta, pagos registrados y devoluciones.
Se reinician las secuencias de identidad y se cargan los detalles correspondientes a cada transacción comercial.
Estos datos permiten evaluar la trazabilidad completa del ciclo de ventas y gestión de cartera.

```sql
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

Se establecen consultas analíticas para el seguimiento de cartera, saldos de pedidos e impacto de devoluciones.
- Muestra el estado de cartera y saldos pendientes de pago asociados a cada pedido de venta.
- Muestra el impacto monetario y las condiciones de los productos en las devoluciones registradas.

```sql
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

-- 2. PEDIDOS DE VENTA
CREATE TABLE pedidos_venta (
    id_pedido       INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_sede         INT NOT NULL,
    id_almacen      INT NOT NULL,
    id_cliente      INT NOT NULL
        CONSTRAINT fk_pedido_cliente REFERENCES clientes(id_cliente),
    id_empleado     INT NOT NULL,
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
    cantidad            INT NOT NULL CHECK (cantidad > 0),
    condicion_producto  VARCHAR(20) NOT NULL
        CHECK (condicion_producto IN ('buen_estado', 'defectuoso', 'empaque_abierto')),
    PRIMARY KEY (id_devolucion, id_producto)
);
```

---

## 6. Identidad

Actúa como módulo de seguridad y de administración de personal: empleados, cuentas de usuario y registro centralizado de auditoría.

Se implementan las tablas de empleados, credenciales de usuario e historial de auditoría de accesos.
Se definen restricciones de unicidad en documentos de identidad, nombres de usuario y llaves foráneas asociadas.
Se configuran los campos de auditoría temporal con marcas de tiempo automáticas para cada operación de sistema.

```sql
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

Se realiza la carga inicial de datos para empleados de distintas sedes, credenciales cifradas y eventos de auditoría.
Se reinician las secuencias de identidad correspondientes para asegurar la continuidad numérica de los registros.
Se simulan múltiples eventos de acceso y acciones sobre recursos del sistema en un rango de fechas específico.

```sql
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

Se ejecutan consultas de conteo, distribución de personal y revisión del registro de auditoría.
- Muestra el conteo de empleados, cuentas de usuario y registros en la bitácora de auditoría.
- Muestra los empleados vinculados a procesos de compras e inventarios.
- Muestra la distribución y conteo de empleados organizados por sede.
- Muestra el conteo de personal agrupado según su cargo corporativo.
- Muestra los empleados que actualmente no disponen de cuenta de usuario asignada.
- Muestra las estadísticas resumidas y rangos de fechas del registro histórico de auditoría de accesos.
- Valida restricciones de unicidad de cuentas, llaves foráneas y estados de empleados.

```sql
-- Conteos.
SELECT 'empleados' AS tabla, count(*) AS filas FROM identidad.empleados
UNION ALL SELECT 'usuarios', count(*) FROM identidad.usuarios
UNION ALL SELECT 'auditoria_accesos', count(*) FROM identidad.auditoria_accesos;

-- Empleados que ya usan compras e inventarios
SELECT id_empleado, nombre_completo, cargo, id_sede FROM identidad.empleados WHERE id_empleado IN (10, 11) ORDER BY id_empleado;

-- Empleados por sede 
SELECT id_sede, count(*) AS empleados FROM identidad.empleados GROUP BY id_sede ORDER BY id_sede;

-- Empleados por cargo.
SELECT cargo, count(*) FROM identidad.empleados GROUP BY cargo ORDER BY cargo;

-- Empleados sin cuenta de usuario
SELECT e.id_empleado, e.nombre_completo FROM identidad.empleados e
WHERE NOT EXISTS (SELECT 1 FROM identidad.usuarios u WHERE u.id_empleado = e.id_empleado) ORDER BY e.id_empleado;

-- Auditoría. 
SELECT accion, count(*) FROM identidad.auditoria_accesos GROUP BY accion ORDER BY accion;
SELECT min(fecha_hora) AS primera, max(fecha_hora) AS ultima FROM identidad.auditoria_accesos;

-- Pruebas de restricciones 
INSERT INTO identidad.usuarios (id_empleado, nombre_usuario, password_hash, estado) VALUES (1, 'otro', 'x', 'activo');   -- UNIQUE (el empleado 1 ya tiene cuenta)
INSERT INTO identidad.usuarios (id_empleado, nombre_usuario, password_hash, estado) VALUES (999, 'fantasma', 'x', 'activo'); -- FK (empleado inexistente)
INSERT INTO identidad.empleados (id_sede, num_documento, nombre_completo, cargo, estado) VALUES (1, '1020304001', 'Repetido', 'Vendedor', 'activo'); -- UNIQUE (documento)
UPDATE identidad.empleados SET estado = 'despedido' WHERE id_empleado = 1;                                                -- CHECK IN (estado)
```