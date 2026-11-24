from app.shared.dependencies import get_service_db

get_compras_db = get_service_db("compras")

__all__ = ["get_compras_db"]
