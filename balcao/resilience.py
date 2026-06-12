"""Resiliencia do gateway: retry pra falha passageira e circuit breaker
pra fonte caida, pra nao martelar quem ja esta no chao."""

import time

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)


def falha_transitoria(exc: BaseException) -> bool:
    # vale tentar de novo: problema de rede ou 5xx da fonte; 4xx nao
    if isinstance(exc, httpx.TransportError):
        return True
    return isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code >= 500


def com_retry(tentativas: int) -> AsyncRetrying:
    return AsyncRetrying(
        stop=stop_after_attempt(tentativas),
        wait=wait_exponential(multiplier=0.2, max=2),
        retry=retry_if_exception(falha_transitoria),
        reraise=True,
    )


class CircuitBreaker:
    """Abre depois de muitas falhas seguidas e poupa a fonte por um tempo.
    Passado o cooldown deixa passar uma sondagem: sucesso fecha o circuito,
    falha abre de novo."""

    def __init__(
        self,
        limite_falhas: int = 5,
        cooldown: float = 30.0,
        timer=time.monotonic,
    ):
        self.limite_falhas = limite_falhas
        self.cooldown = cooldown
        self._timer = timer
        self._falhas = 0
        self._aberto_em: float | None = None

    @property
    def aberto(self) -> bool:
        if self._aberto_em is None:
            return False
        if self._timer() - self._aberto_em >= self.cooldown:
            return False
        return True

    def registra_sucesso(self) -> None:
        self._falhas = 0
        self._aberto_em = None

    def registra_falha(self) -> None:
        self._falhas += 1
        if self._falhas >= self.limite_falhas:
            self._aberto_em = self._timer()
