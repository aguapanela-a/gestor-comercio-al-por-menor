# Backend

Backend compuesto por siete aplicaciones FastAPI independientes. Cada servicio
usa únicamente la conexión configurada para su propia base de datos. No se crean
bases de datos, extensiones ni objetos de PostgreSQL desde este backend.

## Requisitos y configuración

- Python 3.13.
- PostgreSQL Azure Flexible Server accesible desde el entorno de ejecución.
- Variables de entorno definidas en `.env` a partir de `.env.example`.

Desde PowerShell, en la carpeta `backend`:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Completa `.env` localmente con las credenciales de las bases existentes. No
compartas ni confirmes ese archivo. Configura `DATABASE_SSLMODE=require` para
mantener SSL con Azure. La aplicación no conecta a la base durante la
importación; las conexiones se abren cuando se consulta `/health/database` o se
usa una dependencia de base de datos.

## Servicios y puertos

Ejecuta cada comando desde `backend` en una terminal independiente:

| Servicio | Base de datos | Puerto | Comando |
| --- | --- | ---: | --- |
| Identidad | `identidad_db` | 8001 | `python -m uvicorn app.services.identidad.main:app --host 127.0.0.1 --port 8001` |
| Catálogo | `catalogo_db` | 8002 | `python -m uvicorn app.services.catalogo.main:app --host 127.0.0.1 --port 8002` |
| Organización | `organizacion_db` | 8003 | `python -m uvicorn app.services.organizacion.main:app --host 127.0.0.1 --port 8003` |
| Compras | `compras_db` | 8004 | `python -m uvicorn app.services.compras.main:app --host 127.0.0.1 --port 8004` |
| Inventarios | `inventarios_db` | 8005 | `python -m uvicorn app.services.inventarios.main:app --host 127.0.0.1 --port 8005` |
| Ventas | `ventas_db` | 8006 | `python -m uvicorn app.services.ventas.main:app --host 127.0.0.1 --port 8006` |
| Reportes | `reportes_db` | 8007 | `python -m uvicorn app.services.reportes.main:app --host 127.0.0.1 --port 8007` |

Cada aplicación publica `GET /health`, `GET /health/database` y Swagger en
`/docs`. La base `reportes_db` sigue apuntando al servidor PostgreSQL de
Organización según la configuración existente.

## Pruebas

Desde `backend`, ejecuta:

```powershell
python -m pytest
```

Las pruebas usan mocks/dependencias sustituidas para no conectarse a Azure ni
escribir en bases reales.

## APIs de negocio implementadas

Todas las rutas de negocio requieren `Authorization: Bearer <token>`. Las únicas
rutas públicas son las de salud y `POST /auth/login`.

| API | Rutas disponibles |
| --- | --- |
| Identidad | `POST /auth/login`, `GET /auth/me`, `POST /auth/password`, `GET /auth/audit`; CRUD protegido de `/employees` y `/users` (DELETE inactiva, no elimina físicamente). |
| Catálogo | CRUD protegido de `/categories` y `/products` (DELETE inactiva). Los listados aceptan filtros y paginación. |
| Organización | CRUD protegido de `/sedes` y `/warehouses` (DELETE inactiva). Los listados aceptan filtros y paginación. |
| Compras | CRUD protegido de `/suppliers`; lectura de `/product-suppliers`, `/purchase-orders` y `/receipts`; `POST /purchase-orders`, recepción acumulada en `POST /receipts/purchase-orders/{id_orden_compra}` y cancelación de órdenes pendientes. |
| Inventarios | Lectura de `/stock`, alertas en `/stock/alerts`, actualización de mínimos, ajuste absoluto en `POST /stock/adjustments`, creación/consulta de `/transfers`, despacho, recepción acumulada y cancelación de transferencias solicitadas. |
| Ventas | CRUD protegido de `/customers` (DELETE inactiva); creación y consulta de `/orders` y sus detalles; registro de pagos, consulta de `/orders/{id_pedido}/balance`, y solicitud, consulta, aprobación y rechazo de devoluciones. Los pedidos se consultan desde sus cuatro fragmentos operativos. |

Los filtros de listados admiten paginación con `limit` entre 1 y 100 y `offset`
entre 0 y 100000. Los detalles individuales responden 404 cuando el recurso no
existe. Los endpoints de escritura solo aceptan campos definidos en sus schemas;
las contraseñas se cambian por una ruta separada y se almacenan con Argon2.

### Ejemplos

Inicio de sesión:

```http
POST /auth/login
Content-Type: application/json

{"nombre_usuario":"usuario","password":"contraseña"}
```

Consulta autenticada de productos:

```http
GET /products?estado=activo&id_categoria=2&q=cafe&limit=20&offset=0
Authorization: Bearer <token>
```

Creación de categoría:

```http
POST /categories
Authorization: Bearer <token>
Content-Type: application/json

{"nombre":"Bebidas","descripcion":"Bebidas envasadas","estado":"activo"}
```

Consulta de inventario bajo el mínimo:

```http
GET /stock/alerts?id_sede=1&limit=50
Authorization: Bearer <token>
```

Las referencias entre servicios se validan mediante HTTP, reenviando el JWT del
usuario. Las URLs se configuran con `IDENTIDAD_SERVICE_URL`,
`CATALOGO_SERVICE_URL`, `ORGANIZACION_SERVICE_URL`, `COMPRAS_SERVICE_URL`,
`INVENTARIOS_SERVICE_URL` y `VENTAS_SERVICE_URL`; el timeout se controla con
`SERVICE_HTTP_TIMEOUT_SECONDS`.

### Límites de consistencia e idempotencia

Las escrituras dentro de cada servicio son transaccionales. El despacho bloquea
la transferencia y las existencias antes de descontar; la recepción de una
transferencia y la recepción de una orden aceptan cantidades acumuladas, por lo
que reenviar el mismo total no repite el movimiento. Los ajustes de stock fijan
una existencia objetivo, no aplican un delta. Las operaciones de escritura
limitan el bloqueo de filas a 3 segundos y cada sentencia a 15 segundos; las
llamadas HTTP a servicios propietarios usan `SERVICE_HTTP_TIMEOUT_SECONDS`.

El esquema no contiene claves de idempotencia ni un diario de movimientos. Por
eso, la creación de pedidos/órdenes, pagos y solicitudes de devolución puede
duplicarse si el cliente reintenta una petición cuyo resultado quedó ambiguo.
No se declara idempotencia durable para esas escrituras. Tampoco existe una
transacción atómica entre servicios: Compras registra recepciones localmente
pero no actualiza Inventarios; Ventas consulta existencias al crear un pedido,
pero no las reserva/descuenta; aprobar una devolución tampoco repone stock.
Garantizar esos efectos cruzados requiere persistencia de operaciones/reintentos
o un mecanismo de reserva compartido, que no existe en el esquema actual.

Inventarios no tiene una tabla de movimientos: el historial consultable se
limita a transferencias, y los ajustes solo actualizan la existencia actual.
Reportes permanece fuera del alcance y no se modificó.
