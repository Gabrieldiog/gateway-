import httpx

from balcao.config import Settings


def cria_client(settings: Settings) -> httpx.AsyncClient:
    # um client unico pra app inteira, pra aproveitar o pool de conexoes
    return httpx.AsyncClient(
        timeout=httpx.Timeout(settings.http_timeout, connect=5.0),
        headers={
            "Accept": "application/json",
            "User-Agent": "balcao/0.1 (gateway de dados publicos, projeto de portfolio)",
        },
        follow_redirects=True,
    )
