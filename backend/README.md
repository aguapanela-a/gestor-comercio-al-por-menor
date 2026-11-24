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
| Compras | CRUD protegido de `/suppliers`; lectura de `/product-suppliers`, `/purchase-orders` y `/receipts`; cancelación de órdenes pendientes. |
| Inventarios | Lectura de `/stock`, alertas en `/stock/alerts`, actualización de `/stock/minimum` y lectura de `/transfers` y sus detalles. |
| Ventas | CRUD protegido de `/customers` (DELETE inactiva); lectura de `/orders` y sus detalles, pagos y devoluciones. Los pedidos se consultan desde sus cuatro fragmentos operativos. |

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

### Operaciones pendientes

No se implementaron escrituras de órdenes/recepciones de Compras, movimientos y
transferencias de Inventarios, ni creación de pedidos, pagos y devoluciones de
Ventas. Esas operaciones requieren idempotencia durable y consistencia ante
reintentos entre servicios; las tablas existentes no proporcionan claves ni
registros persistentes para ello. No se simulan transacciones distribuidas ni se
declaran exitosas esas operaciones. Reportes permanece fuera del alcance de este
backend y no se modificó.
