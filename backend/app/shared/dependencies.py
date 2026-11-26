from collections.abc import Callable, Generator

from sqlalchemy.orm import Session

from app.core.database import get_db


def get_service_db(service: str) -> Callable[..., Generator[Session, None, None]]:
    def dependency() -> Generator[Session, None, None]:
        database = get_db(service)
        try:
            yield next(database)
        finally:
            database.close()

    return dependency
