from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Balcão"
    debug: bool = False
    http_timeout: float = 15.0
    cache_ttl: int = 600
    cache_stale_ttl: int = 86400
    rate_limit: str = "100/minute"  # o teto de cada balde (por IP ou por chave)
    # chaves de acesso da própria API do Balcão (demo): CSV no .env. Quem manda
    # uma chave válida ganha um balde só seu, isolado do IP compartilhado — o
    # modelo do brapi/DataJud. Vazio = todo mundo é anônimo (balde por IP).
    api_keys: str = ""
    retry_tentativas: int = 3
    breaker_falhas: int = 5
    breaker_cooldown: float = 30.0
    # chaves de fontes que exigem cadastro (gratis); vazio = fonte desativada
    transparencia_api_key: str = ""
    brapi_token: str = ""
    # a do DataJud e PUBLICA (o CNJ publica na wiki e rotaciona de tempos em tempos)
    datajud_api_key: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
