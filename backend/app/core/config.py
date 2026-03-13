from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = PROJECT_ROOT / "backend"
DATA_ROOT = PROJECT_ROOT / "data"
DEFAULT_DB_PATH = DATA_ROOT / "ethicalsiteinspector.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(BACKEND_ROOT / ".env", PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "EthicalSiteInspector API"
    app_env: str = "development"
    api_prefix: str = "/api"
    configured_mode: str = Field(default="auto", alias="AUDIT_MODE")
    use_real_browser: bool = Field(default=False, alias="USE_REAL_BROWSER")
    database_url: str = Field(
        default=f"sqlite:///{DEFAULT_DB_PATH.as_posix()}",
        alias="DATABASE_URL",
    )
    local_storage_root: Path = Field(default=DATA_ROOT, alias="LOCAL_STORAGE_ROOT")
    screenshots_dir: Path = Field(default=DATA_ROOT / "screenshots", alias="SCREENSHOTS_DIR")
    reports_dir: Path = Field(default=DATA_ROOT / "reports", alias="REPORTS_DIR")
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"],
        alias="CORS_ORIGINS",
    )

    aws_region: str = Field(default="us-east-1", alias="AWS_REGION")
    nova_model_id: str = Field(default="us.amazon.nova-pro-v1:0", alias="NOVA_MODEL_ID")
    aws_access_key_id: str | None = Field(default=None, alias="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str | None = Field(default=None, alias="AWS_SECRET_ACCESS_KEY")
    aws_session_token: str | None = Field(default=None, alias="AWS_SESSION_TOKEN")

    s3_bucket_name: str | None = Field(default=None, alias="S3_BUCKET_NAME")
    s3_endpoint_url: str | None = Field(default=None, alias="S3_ENDPOINT_URL")
    s3_public_base_url: str | None = Field(default=None, alias="S3_PUBLIC_BASE_URL")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, list):
            return value
        return [origin.strip() for origin in value.split(",") if origin.strip()]

    @property
    def nova_ready(self) -> bool:
        return bool(self.aws_access_key_id and self.aws_secret_access_key)

    @property
    def s3_ready(self) -> bool:
        return bool(self.s3_bucket_name and self.s3_endpoint_url)

    @property
    def effective_mode(self) -> str:
        mode = self.configured_mode.lower()
        if mode == "mock":
            return "mock"
        if mode == "hybrid":
            return "hybrid" if self.use_real_browser else "mock"
        if mode == "live":
            if self.use_real_browser and self.nova_ready:
                return "live"
            if self.use_real_browser:
                return "hybrid"
            return "mock"
        if self.use_real_browser and self.nova_ready:
            return "live"
        if self.use_real_browser:
            return "hybrid"
        return "mock"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.local_storage_root.mkdir(parents=True, exist_ok=True)
    settings.screenshots_dir.mkdir(parents=True, exist_ok=True)
    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    return settings
