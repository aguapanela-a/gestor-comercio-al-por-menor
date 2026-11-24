from app.shared.dependencies import get_service_db

get_catalogo_db = get_service_db("catalogo")

__all__ = ["get_catalogo_db"]
