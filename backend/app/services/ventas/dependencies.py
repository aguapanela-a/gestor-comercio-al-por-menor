from app.shared.dependencies import get_service_db

get_ventas_db = get_service_db("ventas")

__all__ = ["get_ventas_db"]
