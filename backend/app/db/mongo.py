from functools import lru_cache
from typing import Optional

from pymongo import MongoClient

from app.core.config import settings


@lru_cache
def get_client() -> MongoClient:
    if not settings.mongo_uri:
        raise RuntimeError("MONGO_URI is not configured.")
    return MongoClient(settings.mongo_uri)


def get_db():
    client = get_client()
    db_name = settings.mongo_db or "salon"
    return client[db_name]


def ping_database() -> dict[str, str]:
    client = get_client()
    try:
        client.admin.command("ping")
        return {"database": "ok"}
    except Exception:
        raise
