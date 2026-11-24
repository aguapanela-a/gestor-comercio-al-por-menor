from app.services.identidad.main import app as identidad
from app.services.catalogo.main import app as catalogo
from app.services.organizacion.main import app as organizacion
from app.services.compras.main import app as compras
from app.services.inventarios.main import app as inventarios
from app.services.ventas.main import app as ventas
from app.services.reportes.main import app as reportes

apps = {"identidad": identidad, "catalogo": catalogo, "organizacion": organizacion, "compras": compras, "inventarios": inventarios, "ventas": ventas, "reportes": reportes}

for name, app in apps.items():
    paths = sorted(app.openapi()["paths"])
    print(f"{name}: {len(paths)} rutas registradas - {paths}")
