from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Salon Analytics Platform"
    app_env: str = "local"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    backend_cors_origins: str = "http://localhost:5173,http://localhost:3000"

    database_url: str = Field(default="")

    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    supabase_s3_endpoint: str = ""
    supabase_s3_region: str = "ap-south-1"
    supabase_s3_bucket: str = "salon-assets"
    supabase_s3_access_key_id: str = ""
    supabase_s3_secret_access_key: str = ""

    data_raw_dir: Path = Path("../data/raw")
    data_profile_path: Path = Path("../data/profile.json")

    @field_validator(
        "database_url",
        "supabase_url",
        "supabase_anon_key",
        "supabase_service_role_key",
        "supabase_s3_endpoint",
        "supabase_s3_region",
        "supabase_s3_bucket",
        "supabase_s3_access_key_id",
        "supabase_s3_secret_access_key",
        mode="before",
    )
    @classmethod
    def strip_wrapping_quotes(cls, value):
        if not isinstance(value, str):
            return value
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            return value[1:-1]
        return value

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.backend_cors_origins.split(",")
            if origin.strip()
        ]

    @property
    def project_root(self) -> Path:
        return Path(__file__).resolve().parents[3]

    def resolve_path(self, path: Path) -> Path:
        if path.is_absolute():
            return path
        return (self.project_root / path).resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
