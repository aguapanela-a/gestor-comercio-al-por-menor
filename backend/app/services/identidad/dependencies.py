from app.shared.dependencies import get_service_db

get_identity_db = get_service_db("identidad")

__all__ = ["get_identity_db"]
