"""
UAEF Configuration Management

Centralized configuration using Pydantic Settings for type-safe
environment variable handling and validation.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Database connection configuration."""

    model_config = SettingsConfigDict(env_prefix="UAEF_DB_")

    url: str = Field(
        default="postgresql://localhost:5432/uaef",
        description="Database connection URL (PostgreSQL or SQLite)",
    )
    pool_size: int = Field(default=5, ge=1, le=20)
    max_overflow: int = Field(default=10, ge=0, le=50)
    pool_recycle: int = Field(default=3600, description="Connection recycle time in seconds")
    echo: bool = Field(default=False, description="Echo SQL statements")


class SecuritySettings(BaseSettings):
    """Security and authentication configuration."""

    model_config = SettingsConfigDict(env_prefix="UAEF_SECURITY_")

    jwt_secret: SecretStr = Field(
        default="change-me-in-production",
        description="Secret key for JWT signing",
    )
    jwt_algorithm: str = Field(default="HS256")
    jwt_expiration_hours: int = Field(default=24, ge=1)
    encryption_key: SecretStr = Field(
        default="change-me-in-production-32bytes",
        description="32-byte key for data encryption",
    )


class LedgerSettings(BaseSettings):
    """Trust ledger configuration."""

    model_config = SettingsConfigDict(env_prefix="UAEF_LEDGER_")

    hash_algorithm: str = Field(default="sha256")
    require_signature: bool = Field(default=True)
    checkpoint_interval: int = Field(
        default=100,
        description="Number of events between automatic checkpoints",
    )


class AgentSettings(BaseSettings):
    """Agent orchestration configuration."""

    model_config = SettingsConfigDict(env_prefix="UAEF_AGENT_")

    anthropic_api_key: SecretStr = Field(
        default="",
        description="Anthropic API key for Claude agents",
    )
    default_model: str = Field(default="claude-sonnet-4-20250514")
    max_concurrent_agents: int = Field(default=10, ge=1)
    task_timeout_seconds: int = Field(default=300, ge=30)
    max_retries: int = Field(default=3, ge=0)


class SettlementSettings(BaseSettings):
    """Incentive settlement engine configuration."""

    model_config = SettingsConfigDict(env_prefix="UAEF_SETTLEMENT_")

    default_currency: str = Field(default="USD")
    auto_settle: bool = Field(default=False)
    settlement_batch_size: int = Field(default=100, ge=1)


class Settings(BaseSettings):
    """Main UAEF configuration."""

    model_config = SettingsConfigDict(
        env_prefix="UAEF_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="UAEF")
    environment: Literal["development", "staging", "production"] = Field(
        default="development"
    )
    debug: bool = Field(default=False)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO")

    # Nested settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    ledger: LedgerSettings = Field(default_factory=LedgerSettings)
    agent: AgentSettings = Field(default_factory=AgentSettings)
    settlement: SettlementSettings = Field(default_factory=SettlementSettings)

    # AWS/Serverless
    aws_region: str = Field(default="us-east-1")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
