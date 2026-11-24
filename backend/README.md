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

## Alcance actual

Se conservó el inicio de sesión existente de Identidad, incluida la aceptación
temporal de hashes SHA-256 heredados y su actualización a Argon2 al autenticar
correctamente. Los demás módulos funcionales y sus esquemas quedan pendientes
de inspeccionar las tablas reales; no se han añadido modelos ni operaciones
CRUD.
