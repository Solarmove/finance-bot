from functools import lru_cache
from typing import Annotated
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AfterValidator, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _without_trailing_slash(value: str) -> str:
    return value.rstrip("/")


BaseUrl = Annotated[str, AfterValidator(_without_trailing_slash)]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    bot_token: SecretStr
    webhook_base_url: BaseUrl
    webhook_path: str = "/telegram/webhook"
    webhook_secret: SecretStr

    database_url: str = "postgresql+asyncpg://finance:finance@localhost:5432/finance"
    redis_url: str = "redis://localhost:6379/0"

    default_currency: str = Field(default="PLN", min_length=3, max_length=3)
    app_timezone: str = "Europe/Warsaw"
    host: str = "0.0.0.0"
    port: int = Field(default=8080, ge=1, le=65535)
    log_level: str = "INFO"
    drop_pending_updates: bool = False

    @field_validator("webhook_path")
    @classmethod
    def validate_webhook_path(cls, value: str) -> str:
        if not value.startswith("/"):
            raise ValueError("WEBHOOK_PATH must start with '/'")
        return value

    @field_validator("webhook_base_url")
    @classmethod
    def require_https_webhook(cls, value: str) -> str:
        if not value.startswith("https://"):
            raise ValueError("WEBHOOK_BASE_URL must use HTTPS")
        return value

    @field_validator("webhook_secret")
    @classmethod
    def validate_webhook_secret(cls, value: SecretStr) -> SecretStr:
        raw = value.get_secret_value()
        if not 1 <= len(raw) <= 256 or not all(char.isalnum() or char in "_-" for char in raw):
            raise ValueError("WEBHOOK_SECRET may contain only A-Z, a-z, 0-9, _ and -")
        return value

    @field_validator("default_currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()

    @field_validator("app_timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as error:
            raise ValueError("APP_TIMEZONE must be a valid IANA timezone") from error
        return value

    @property
    def webhook_url(self) -> str:
        return f"{self.webhook_base_url}{self.webhook_path}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
