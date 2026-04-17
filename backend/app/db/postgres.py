from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.core.config import settings


@lru_cache
def get_engine() -> Engine:
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not configured.")
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=2,
        max_overflow=3,
        pool_recycle=1800,
    )


def db_session() -> Generator:
    engine = get_engine()
    with engine.begin() as connection:
        yield connection


def ping_database() -> dict[str, str]:
    engine = get_engine()
    with engine.connect() as connection:
        value = connection.execute(text("select 'ok'")).scalar_one()
    return {"database": value}
