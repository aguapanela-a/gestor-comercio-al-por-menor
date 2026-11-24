from sqlalchemy import text
from sqlalchemy.orm import Session


def set_local_transaction_timeouts(db: Session) -> None:
    db.execute(text("SET LOCAL lock_timeout = '3s'"))
    db.execute(text("SET LOCAL statement_timeout = '15s'"))


__all__ = ["set_local_transaction_timeouts"]
