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
    max_upload_bytes: int = 50 * 1024 * 1024  # 50 MiB
    allowed_extensions: str = "pdf,doc,docx,txt,md"  # comma-separated
    allowed_content_types: str = "application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,text/markdown"  # comma-separated


class PostgresSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="POSTGRES_", extra="ignore")
    host: str = "localhost"
    port: int = 5432
    user: str = "postgres"
    password: str = ""
    db: str = "app"

    @property
    def dsn(self) -> str:
        return f"postgresql+psycopg://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"


class RedisSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="REDIS_", extra="ignore")
    url: str = "redis://localhost:6379/0"


class S3Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="S3_", extra="ignore")
    endpoint_url: str = "http://localhost:9000"
    bucket: str = "flow-graph"
    key_prefix: str = ""
    access_key_id: str = ""
    secret_access_key: str = ""


class DoclingSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DOCLING_", extra="ignore")
    enabled: bool = True


class LiteLLMSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LITELLM_", extra="ignore")
    api_key: str = ""
    model: str = "gpt-4o-mini"
    base_url: str | None = None
    fallback_model: str | None = None
    max_retries: int = 0
    request_timeout: int = 60
    repair_max_attempts: int = 0
    # Delay in seconds between LLM calls when processing multiple chunks (avoids 429 on free tier)
    extraction_delay_seconds: float = 10.0


class PrefilterSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PREFILTER_", extra="ignore")
    # Legacy single threshold (used as gray_threshold if accept/gray not set)
    threshold: float = 0.3
    # Weights per feature group (0 = disabled)
    weight_structural_heading: float = 0.15
    weight_structural_table_list: float = 0.1
    weight_structural_depth: float = 0.05
    weight_structural_appendix_penalty: float = -0.1
    weight_exact_match: float = 0.25
    weight_pattern: float = 0.2
    weight_context_boost: float = 0.15
    weight_lexical: float = 0.1
    # Thresholds: score >= accept -> keep; gray_threshold <= score < accept -> gray; < gray_threshold -> reject
    accept_threshold: float = 0.4
    gray_threshold: float = 0.2
    top_gray_budget_per_document: int = 10
    gray_adjacent_to_accepted: bool = True
    # Lexicon and resources
    lexicon_dir: str = "data/prefilter"
    spacy_model: str = "en_core_web_sm"
    enable_pattern_matching: bool = True


class NormalizationSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="NORMALIZATION_", extra="ignore")
    config_dir: str = "data/normalization"
    normalization_version: str = "v1"


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="WORKER_", extra="ignore")
    concurrency: int = 2
    queue_name: str = "default"
    # Max time a single run job may run (parse + chunk + prefilter + extract + persist). ARQ default is 300s.
    job_timeout_seconds: int = 900


class QdrantSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="QDRANT_", extra="ignore")
    enabled: bool = False
    url: str = "http://localhost:6333"


class ObservabilitySettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OBS_", extra="ignore")
    log_level: str = "INFO"
    enable_debug_artifacts: bool = False
    step_timeout_seconds: int | None = None


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
    use_fake_adapters: bool = Field(
        default=False, description="USE_FAKE_ADAPTERS: use in-memory storage/queue instead of S3/Redis"
    )
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
    normalization: NormalizationSettings = Field(default_factory=NormalizationSettings)
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
