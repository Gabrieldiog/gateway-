"""Cache TTL em memoria: a mesma consulta dentro da janela nem chega na
fonte, o que protege os limites de quem esta atras do gateway."""

import time

from cachetools import TTLCache

from balcao.connectors.base import NormalizedResponse


class CacheRespostas:
    def __init__(self, ttl: int, max_itens: int = 2048, timer=time.monotonic):
        self._itens: TTLCache = TTLCache(maxsize=max_itens, ttl=ttl, timer=timer)

    @staticmethod
    def chave(fonte: str, recurso: str, params: dict) -> str:
        query = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        return f"{fonte}:{recurso}?{query}"

    def pega(self, chave: str) -> NormalizedResponse | None:
        return self._itens.get(chave)

    def guarda(self, chave: str, resposta: NormalizedResponse) -> None:
        self._itens[chave] = resposta
