from app.shared.dependencies import get_service_db

get_inventarios_db = get_service_db("inventarios")

__all__ = ["get_inventarios_db"]
