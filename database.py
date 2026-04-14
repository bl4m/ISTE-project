import os
from contextlib import contextmanager
from typing import Optional

from sqlmodel import SQLModel, Session, create_engine

engine = create_engine("sqlite:///project.db", echo=False, future=True)


def init_db(engine_override: Optional[object] = None) -> None:
    """Create all tables from SQLModel metadata.

    Importing the `models` module ensures model classes are registered on SQLModel.metadata.
    """

    # ensure models are imported so tables are present in metadata
    import models  # noqa: F401

    _engine = engine_override or engine
    SQLModel.metadata.create_all(_engine)


@contextmanager
def get_db_session(engine_override: Optional[object] = None):
    """Provide a transactional scope around a series of operations using `sqlmodel.Session`.

    Usage:
        with get_db_session() as session:
            session.add(obj)
            session.flush()
    """

    _engine = engine_override or engine
    session = Session(_engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_session_dependency(engine_override: Optional[object] = None):
    """Dependency for FastAPI to provide a DB session via `with` context.

    Usage in FastAPI endpoints: `session: Session = Depends(get_session_dependency)`
    """
    with get_db_session(engine_override) as session:
        yield session


if __name__ == "__main__":
    init_db()
    print("Database initialized (tables created).")
