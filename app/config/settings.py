"""Centralized settings from environment.

All secrets and configuration come from environment variables (or mounted
secret files). No module other than app.config should read os.environ
for configuration. Settings are immutable after load. Services receive
settings via constructor injection.
"""

from functools import lru_cache
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.errors import ConfigError
from pydantic import ValidationError as PydanticValidationError


# --- Nested settings groups ---


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_", extra="ignore")
    name: str = "flow-graph"


class ApiSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="API_", extra="ignore")
    host: str = "0.0.0.0"
    port: int = 8000


class PostgresSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="POSTGRES_", extra="ignore")
    host: str = "localhost"
    port: int = 5432
    user: str = "postgres"
    password: str = ""
    db: str = "app"

    @property
    def dsn(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"


class RedisSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="REDIS_", extra="ignore")
    url: str = "redis://localhost:6379/0"


class S3Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="S3_", extra="ignore")
    endpoint_url: str = "http://localhost:9000"
    bucket: str = "flow-graph"
    key_prefix: str = ""


class DoclingSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DOCLING_", extra="ignore")
    enabled: bool = True


class LiteLLMSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LITELLM_", extra="ignore")
    api_key: str = ""
    model: str = "gpt-4o-mini"
    base_url: str | None = None


class PrefilterSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PREFILTER_", extra="ignore")
    threshold: float = 0.3


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="WORKER_", extra="ignore")
    concurrency: int = 2
    queue_name: str = "default"


class QdrantSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="QDRANT_", extra="ignore")
    enabled: bool = False
    url: str = "http://localhost:6333"


class ObservabilitySettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OBS_", extra="ignore")
    log_level: str = "INFO"


# --- Root settings ---


class Settings(BaseSettings):
    """Immutable root settings. Load via get_settings()."""

    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        extra="ignore",
        frozen=True,
    )

    # Required so we can test "missing required" and "loads valid"
    environment: str = Field(..., description="APP_ENVIRONMENT or ENVIRONMENT")

    # Feature flags (explicit booleans)
    enable_qdrant: bool = Field(default=False, description="ENABLE_QDRANT")
    enable_llm_cache: bool = Field(default=False, description="ENABLE_LLM_CACHE")
    enable_prefilter_debug_fields: bool = Field(
        default=False, description="ENABLE_PREFILTER_DEBUG_FIELDS"
    )

    app: AppSettings = Field(default_factory=AppSettings)
    api: ApiSettings = Field(default_factory=ApiSettings)
    postgres: PostgresSettings = Field(default_factory=PostgresSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    s3: S3Settings = Field(default_factory=S3Settings)
    docling: DoclingSettings = Field(default_factory=DoclingSettings)
    litellm: LiteLLMSettings = Field(default_factory=LiteLLMSettings)
    prefilter: PrefilterSettings = Field(default_factory=PrefilterSettings)
    worker: WorkerSettings = Field(default_factory=WorkerSettings)
    qdrant: QdrantSettings = Field(default_factory=QdrantSettings)
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)


def get_settings(**overrides: Any) -> Settings:
    """Load and validate settings from environment. Cached after first call when no overrides."""
    if overrides:
        try:
            return Settings(**overrides)
        except PydanticValidationError as e:
            raise ConfigError(f"Invalid configuration: {e!s}") from e
    return _get_settings_cached()


@lru_cache(maxsize=1)
def _get_settings_cached() -> Settings:
    """Internal cached loader. Use get_settings() and reset_settings_cache() in tests."""
    try:
        return Settings()
    except PydanticValidationError as e:
        raise ConfigError(f"Invalid configuration: {e!s}") from e


def reset_settings_cache() -> None:
    """Clear the settings cache. Call in tests before changing env to get a fresh load."""
    _get_settings_cached.cache_clear()
