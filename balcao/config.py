from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Balcão"
    debug: bool = False
    http_timeout: float = 15.0
    cache_ttl: int = 600
    cache_stale_ttl: int = 86400
    # cache curto das fontes tempo-real (câmbio): frescor de segundos sem
    # martelar a fonte a cada request, a AwesomeAPI rate-limita IP fixo
    cache_vivo_ttl: int = 45
    rate_limit: str = "2000/minute"  # o teto de cada balde (por IP ou por chave)
    # origens liberadas pra chamar o Balcão do navegador (CSV). Como a API é só
    # leitura (GET), CORS aqui é só pra um front conseguir consumir. Default cobre
    # as portas de dev + o comparador de remédio publicado; pra somar outros
    # sites, aponta via CORS_ORIGINS no .env (substitui esta lista).
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000,https://pharmacy-price.netlify.app"
    # chaves de acesso da própria API do Balcão (demo): CSV no .env. Quem manda
    # uma chave válida ganha um balde só seu, isolado do IP compartilhado; o
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
    # AwesomeAPI (cambio): OPCIONAL, so melhora a cota. Sem token o limite e
    # ~100 req e a fonte trava IP de datacenter; o token gratuito (cadastro) da
    # 100 mil/mes. Vazio = tenta sem token e, se recusarem, cai pro plano B em
    # fontes abertas (ver balcao/connectors/cotacoes.py).
    awesomeapi_token: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
