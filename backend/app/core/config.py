"""Application configuration."""
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "Team1 Backend API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = Field(default="development", description="Environment: development, staging, production")

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://user:password@localhost:5432/team1",
        description="Async PostgreSQL connection URL",
    )
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 3600

    # Redis
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )
    REDIS_POOL_SIZE: int = 50

    # Security
    SECRET_KEY: str = Field(
        default="change-this-secret-key-in-production",
        description="Secret key for JWT encoding",
    )
    SECRET_KEY_MIN_LENGTH: int = Field(default=32, description="Minimum required SECRET_KEY length")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    def validate_security_config(self) -> None:
        """Validate security-critical configuration.

        Raises:
            ValueError: If security configuration is invalid
        """
        # Check SECRET_KEY in production
        if self.ENVIRONMENT == "production":
            if self.SECRET_KEY in [
                "change-this-secret-key-in-production",
                "",
                "change-this-secret-key",
            ]:
                raise ValueError(
                    "SECURITY: SECRET_KEY must be set to a secure value in production"
                )

            if len(self.SECRET_KEY) < self.SECRET_KEY_MIN_LENGTH:
                raise ValueError(
                    f"SECURITY: SECRET_KEY must be at least {self.SECRET_KEY_MIN_LENGTH} characters"
                )

        # Check database URL
        if "user:password" in self.DATABASE_URL or "localhost:5432" in self.DATABASE_URL:
            if self.ENVIRONMENT == "production":
                raise ValueError(
                    "SECURITY: Default database credentials detected in production"
                )

    # CORS
    CORS_ORIGINS: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        description="Allowed CORS origins",
    )

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_BURST: int = 100

    # Observability
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json or console
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4317"
    OTEL_SERVICE_NAME: str = "team1-backend"

    # AI Services
    AI_SERVICE_URL: str = Field(default="", description="AI service URL (e.g., Ollama)")
    AI_API_KEY: str = Field(default="", description="OpenAI API key")
    AI_EMBEDDING_PROVIDER: str = Field(default="openai", description="Embedding provider: openai or ollama")
    AI_EMBEDDING_MODEL: str = Field(default="text-embedding-3-small", description="Embedding model name")
    AI_LLM_PROVIDER: str = Field(default="openai", description="LLM provider: openai or ollama")
    AI_LLM_MODEL: str = Field(default="gpt-4o-mini", description="LLM model name")
    AI_SERVICE_TIMEOUT: int = Field(default=30, description="AI service timeout in seconds")

    # File Storage
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    UPLOAD_DIR: Path = Field(default=Path("uploads"))

    @property
    def sync_database_url(self) -> str:
        """Get sync database URL for migrations."""
        return self.DATABASE_URL.replace("+asyncpg", "")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
