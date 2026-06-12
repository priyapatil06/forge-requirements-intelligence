from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    forge_env: Literal["development", "test", "production"] = "development"
    forge_secret_key: str = "development-only-change-me"
    forge_frontend_url: str = "http://localhost:5173"
    forge_cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    forge_database_url: str = "sqlite:///./forge.db"
    forge_mock_llm: bool = True
    forge_token_encryption_key: str | None = None

    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-6"

    atlassian_client_id: str | None = None
    atlassian_client_secret: str | None = None
    atlassian_redirect_uri: str = "http://localhost:8000/api/v1/jira/callback"
    atlassian_scopes: str = (
        "read:jira-work write:jira-work read:jira-user offline_access"
    )

    @property
    def cors_origins(self) -> list[str]:
        return [item.strip() for item in self.forge_cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
