from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from services.shared.config import settings

Base = declarative_base()
engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from services.shared import models  # noqa: F401

    if engine.dialect.name == "postgresql":
        # Serialize create_all across services to prevent concurrent DDL races at startup.
        with engine.begin() as conn:
            conn.execute(text("SELECT pg_advisory_lock(874213)"))
            try:
                Base.metadata.create_all(bind=conn)
            finally:
                conn.execute(text("SELECT pg_advisory_unlock(874213)"))
        return

    Base.metadata.create_all(bind=engine)
