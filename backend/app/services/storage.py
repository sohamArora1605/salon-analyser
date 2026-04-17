from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from uuid import uuid4

from app.core.config import settings


@dataclass(frozen=True)
class UploadedObject:
    bucket: str
    key: str
    public_url: str | None


def get_s3_client():
    try:
        import boto3
        from botocore.client import Config
    except ModuleNotFoundError as exc:
        raise RuntimeError("Install backend requirements before using storage uploads.") from exc

    missing = [
        name
        for name, value in {
            "SUPABASE_S3_ENDPOINT": settings.supabase_s3_endpoint,
            "SUPABASE_S3_ACCESS_KEY_ID": settings.supabase_s3_access_key_id,
            "SUPABASE_S3_SECRET_ACCESS_KEY": settings.supabase_s3_secret_access_key,
        }.items()
        if not value
    ]
    if missing:
        raise RuntimeError(f"Missing storage settings: {', '.join(missing)}")

    return boto3.client(
        "s3",
        endpoint_url=settings.supabase_s3_endpoint,
        aws_access_key_id=settings.supabase_s3_access_key_id,
        aws_secret_access_key=settings.supabase_s3_secret_access_key,
        region_name=settings.supabase_s3_region,
        config=Config(signature_version="s3v4"),
    )


def build_storage_key(filename: str, folder: str = "uploads") -> str:
    safe_name = PurePosixPath(filename).name.replace(" ", "_")
    return str(PurePosixPath(folder) / f"{uuid4().hex}_{safe_name}")


def public_url_for(key: str) -> str | None:
    if not settings.supabase_url or not settings.supabase_s3_bucket:
        return None
    base = settings.supabase_url.rstrip("/")
    return f"{base}/storage/v1/object/public/{settings.supabase_s3_bucket}/{key}"


def upload_bytes(content: bytes, filename: str, content_type: str | None) -> UploadedObject:
    key = build_storage_key(filename)
    client = get_s3_client()
    client.put_object(
        Bucket=settings.supabase_s3_bucket,
        Key=key,
        Body=content,
        ContentType=content_type or "application/octet-stream",
    )
    return UploadedObject(
        bucket=settings.supabase_s3_bucket,
        key=key,
        public_url=public_url_for(key),
    )
