from starlette.requests import Request

from slowapi import Limiter
from slowapi.util import get_remote_address


def le_chaves(bruto: str) -> set[str]:
    return {c.strip() for c in (bruto or "").split(",") if c.strip()}


def extrai_chave(request: Request) -> str | None:
    # a chave vem no header (padrão de API) ou na query (prático pro navegador)
    return request.headers.get("x-api-key") or request.query_params.get("chave")


def cria_limiter(limite: str, chaves: set[str] | None = None) -> Limiter:
    """Cada requisição cai num balde: por chave (se mandou uma válida) ou por
    IP (anônimo). Quem tem chave não disputa o balde do IP compartilhado,
    escritório, faculdade e operadora com NAT deixam de derrubar uns aos outros.
    headers_enabled expõe X-RateLimit-* pra quem consome saber onde está."""
    chaves = chaves or set()

    def balde(request: Request) -> str:
        chave = extrai_chave(request)
        if chave and chave in chaves:
            return f"chave:{chave}"
        return f"ip:{get_remote_address(request)}"

    return Limiter(key_func=balde, default_limits=[limite], headers_enabled=True)
