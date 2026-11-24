from app.shared.dependencies import get_service_db

get_organizacion_db = get_service_db("organizacion")

__all__ = ["get_organizacion_db"]
