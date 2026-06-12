from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Balcão"
    debug: bool = False
    http_timeout: float = 15.0
    cache_ttl: int = 600
    rate_limit: str = "100/minute"


@lru_cache
def get_settings() -> Settings:
    return Settings()
