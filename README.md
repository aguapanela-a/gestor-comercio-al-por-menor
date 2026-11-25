# Gestor de Comercio al por Menor

Proyecto académico para gestionar una empresa simulada de alcance nacional
dedicada a la comercialización y distribución de productos al por menor.

## Requisitos previos

- Windows con PowerShell 5.1 o PowerShell 7.
- Python 3.13.
- Node.js y npm.
- Los servidores PostgreSQL de Azure que usan las APIs deben estar encendidos y
  accesibles para que las bases de datos respondan. El frontend puede iniciar
  aunque Azure no esté disponible; el script informa por separado el estado de
  la API y el de su base de datos.
- Las variables de conexión deben estar configuradas localmente en
  `backend\.env`. No guardes credenciales en los scripts ni las compartas.

## Preparar dependencias

Desde la raíz del repositorio, crea el entorno virtual e instala las
dependencias del backend una sola vez:

```powershell
py -3.13 -m venv .\backend\.venv
.\backend\.venv\Scripts\python.exe -m pip install -r .\backend\requirements.txt
```

Configura `backend\.env` a partir de `backend\.env.example` si aún no existe.
Completa las credenciales localmente; el inicio centralizado no crea ni modifica
credenciales.

Instala las dependencias del frontend una sola vez:

```powershell
Set-Location .\frontend
npm install
Set-Location ..
```

Si `frontend\node_modules` falta al iniciar, el script ofrece ejecutar `npm
install`; no vuelve a instalar dependencias en cada ejecución.

## Iniciar todo el proyecto

Desde la raíz:

```powershell
.\iniciar_proyecto.ps1
```

Si la política local impide ejecutar scripts, puedes usar una política temporal
para esa invocación sin cambiar la configuración global:

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\iniciar_proyecto.ps1
```

El script comprueba los puertos antes de iniciar, abre una terminal visible por
cada servicio y deja sus mensajes y errores disponibles en esas ventanas.
Después comprueba el proceso, el endpoint `/health` y, de forma independiente,
`/health/database`. Este último hace la comprobación de conexión de solo lectura
que ya implementa cada API; no ejecuta DDL ni DML.

| Servicio | Puerto | Swagger |
| --- | ---: | --- |
| Identidad | 8001 | <http://127.0.0.1:8001/docs> |
| Catálogo | 8002 | <http://127.0.0.1:8002/docs> |
| Organización | 8003 | <http://127.0.0.1:8003/docs> |
| Compras | 8004 | <http://127.0.0.1:8004/docs> |
| Inventarios | 8005 | <http://127.0.0.1:8005/docs> |
| Ventas | 8006 | <http://127.0.0.1:8006/docs> |
| Frontend | 5173 | <http://127.0.0.1:5173/> |

El modo opcional `.\iniciar_proyecto.ps1 -CheckOnly` revisa los prerrequisitos,
la importación de módulos y la ocupación de puertos sin iniciar procesos.

## Detener todo

Desde la raíz:

```powershell
.\detener_proyecto.ps1
```

La detención usa el registro local creado por el iniciador, verifica PID,
ejecutable y hora de creación, solicita primero el cierre normal de cada
terminal y después detiene únicamente los procesos registrados y sus hijos.
No termina procesos de Python o Node.js ajenos al proyecto. Si cierras una
terminal manualmente, ejecuta también el script de detención para limpiar
cualquier proceso hijo que pudiera seguir activo.

## Iniciar un servicio individual

Las APIs se pueden iniciar desde una terminal independiente, desde `backend`:

```powershell
Set-Location .\backend
.\.venv\Scripts\python.exe -m uvicorn app.services.identidad.main:app --host 127.0.0.1 --port 8001
```

Sustituye el módulo y puerto según el servicio:

| Servicio | Módulo | Puerto |
| --- | --- | ---: |
| Identidad | `app.services.identidad.main:app` | 8001 |
| Catálogo | `app.services.catalogo.main:app` | 8002 |
| Organización | `app.services.organizacion.main:app` | 8003 |
| Compras | `app.services.compras.main:app` | 8004 |
| Inventarios | `app.services.inventarios.main:app` | 8005 |
| Ventas | `app.services.ventas.main:app` | 8006 |

Para iniciar solo el frontend:

```powershell
Set-Location .\frontend
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

## Si un puerto está ocupado

El iniciador informa el puerto y, cuando Windows permite identificarlo, el
proceso que lo ocupa. No finaliza ese proceso ni inicia una segunda instancia
del servicio. Cierra la aplicación propietaria por sus medios o elige con el
equipo un puerto compatible; los puertos deben coincidir con la configuración
actual del proyecto.

Reportes (puerto 8007) no se inicia ni se modifica desde estos scripts.
