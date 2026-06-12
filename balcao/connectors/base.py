from abc import ABC, abstractmethod
from typing import Any, ClassVar

import httpx
from pydantic import BaseModel, Field

from balcao.exceptions import ErroUpstream
from balcao.resilience import CircuitBreaker, com_retry


class NormalizedResponse(BaseModel):
    """Envelope que toda fonte devolve, independente de como ela responde."""

    fonte: str
    recurso: str
    dados: list[dict]
    total: int | None = None
    meta: dict = Field(default_factory=dict)


class BaseConnector(ABC):
    """Contrato unico das fontes: plugar uma nova = subclasse + @register."""

    name: ClassVar[str]
    base_url: ClassVar[str]
    requires_key: ClassVar[bool] = False
    description: ClassVar[str] = ""
    resources: ClassVar[dict[str, str]] = {}
    suporta_busca: ClassVar[bool] = False

    def __init__(
        self,
        client: httpx.AsyncClient,
        retry_tentativas: int = 3,
        breaker: CircuitBreaker | None = None,
    ):
        self.client = client
        self.retry_tentativas = retry_tentativas
        self.breaker = breaker or CircuitBreaker()

    @abstractmethod
    async def fetch(self, recurso: str, **params: Any) -> NormalizedResponse:
        """Traduz params genericos pra chamada da fonte e devolve dados normalizados."""

    async def buscar(self, q: str) -> list[dict]:
        """Busca generica da fonte, usada pelo /v1/buscar. Quem suporta
        seta suporta_busca = True e implementa."""
        raise NotImplementedError

    async def get_json(self, path: str, params: dict | None = None) -> Any:
        if self.breaker.aberto:
            raise ErroUpstream(self.name, circuito_aberto=True)
        resp: httpx.Response | None = None
        try:
            async for tentativa in com_retry(self.retry_tentativas):
                with tentativa:
                    resp = await self.client.get(f"{self.base_url}{path}", params=params)
                    resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            # 4xx e pedido errado, nao fonte doente; so 5xx conta pro breaker
            if exc.response.status_code >= 500:
                self.breaker.registra_falha()
            raise ErroUpstream(self.name, exc.response.status_code) from exc
        except httpx.HTTPError as exc:
            self.breaker.registra_falha()
            raise ErroUpstream(self.name) from exc
        self.breaker.registra_sucesso()
        return resp.json()


_registry: dict[str, type[BaseConnector]] = {}


def register(cls: type[BaseConnector]) -> type[BaseConnector]:
    if cls.name in _registry:
        raise ValueError(f"conector duplicado: {cls.name}")
    _registry[cls.name] = cls
    return cls


def connector_classes() -> dict[str, type[BaseConnector]]:
    return dict(_registry)
