from sqlalchemy import text
from app.core.database import get_engine

query = text("""SELECT table_name, column_name, data_type, is_nullable FROM information_schema.columns WHERE table_schema = :schema AND table_name IN (:t1, :t2, :t3) ORDER BY table_name, ordinal_position""")

with get_engine("identidad").connect() as connection:
    rows = connection.execute(query, {"schema": "identidad", "t1": "empleados", "t2": "usuarios", "t3": "auditoria_accesos"}).mappings()
    for row in rows:
        print(dict(row))
