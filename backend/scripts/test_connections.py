
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import PurePosixPath
from uuid import uuid4

from sqlalchemy import text

from app.core.config import settings
from app.db.postgres import get_engine
from app.services.storage import get_s3_client


def test_database() -> None:
    print("Testing Supabase Postgres...")
    engine = get_engine()
    with engine.connect() as connection:
        result = connection.execute(text("select 1 as ok")).scalar_one()
    if result != 1:
        raise RuntimeError("Database returned an unexpected result.")
    print("Database connection OK")


def test_storage() -> None:
    print("Testing Supabase S3 Storage...")
    client = get_s3_client()
    bucket = settings.supabase_s3_bucket
    key = str(PurePosixPath("connection-tests") / f"{uuid4().hex}.txt")
    body = f"salon-platform connection test {datetime.now(UTC).isoformat()}".encode("utf-8")

    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=body,
        ContentType="text/plain",
    )

    response = client.get_object(Bucket=bucket, Key=key)
    downloaded = response["Body"].read()
    if downloaded != body:
        raise RuntimeError("Storage object readback did not match uploaded content.")

    client.delete_object(Bucket=bucket, Key=key)
    print(f"Storage connection OK using bucket '{bucket}'")


def main() -> None:
    checks = (
        ("Database", test_database),
        ("Storage", test_storage),
    )
    failures: list[tuple[str, Exception]] = []

    for name, check in checks:
        try:
            check()
        except Exception as exc:
            failures.append((name, exc))
            print(f"{name} connection FAILED: {exc}")

    if failures:
        failed_names = ", ".join(name for name, _ in failures)
        raise SystemExit(f"Connection checks failed: {failed_names}")

    print("All connection checks passed")


if __name__ == "__main__":
    main()
