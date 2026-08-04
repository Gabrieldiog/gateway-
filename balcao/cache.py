"""Cache TTL em memoria: a mesma consulta dentro da janela nem chega na
fonte, o que protege os limites de quem esta atras do gateway."""

import time

from cachetools import TTLCache
from pydantic import BaseModel


class CacheRespostas:
    """Dois niveis: o fresco respeita o TTL normal; o velho dura bem mais
    e so e servido quando a fonte esta fora do ar (stale e melhor que erro).
    O velho carrega a hora em que foi guardado, e o carimbo de honestidade
    que a resposta stale mostra ao leitor."""

    def __init__(
        self,
        ttl: int,
        max_itens: int = 2048,
        stale_ttl: int = 86400,
        timer=time.monotonic,
        relogio=time.time,
    ):
        self._itens: TTLCache = TTLCache(maxsize=max_itens, ttl=ttl, timer=timer)
        self._velhos: TTLCache = TTLCache(maxsize=max_itens, ttl=stale_ttl, timer=timer)
        self._relogio = relogio

    @staticmethod
    def chave(fonte: str, recurso: str, params: dict) -> str:
        query = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        return f"{fonte}:{recurso}?{query}"

    def pega(self, chave: str) -> BaseModel | None:
        return self._itens.get(chave)

    def pega_velho(self, chave: str) -> tuple[BaseModel, float] | None:
        """Retorna (resposta, epoch de quando foi salva) ou None."""
        return self._velhos.get(chave)

    def guarda(self, chave: str, resposta: BaseModel) -> None:
        self._itens[chave] = resposta
        self._velhos[chave] = (resposta, self._relogio())
