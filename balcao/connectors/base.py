from abc import ABC, abstractmethod
from typing import Any, ClassVar

import httpx
from pydantic import BaseModel, Field


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

    def __init__(self, client: httpx.AsyncClient):
        self.client = client

    @abstractmethod
    async def fetch(self, recurso: str, **params: Any) -> NormalizedResponse:
        """Traduz params genericos pra chamada da fonte e devolve dados normalizados."""

    async def get_json(self, path: str, params: dict | None = None) -> Any:
        resp = await self.client.get(f"{self.base_url}{path}", params=params)
        resp.raise_for_status()
        return resp.json()


_registry: dict[str, type[BaseConnector]] = {}


def register(cls: type[BaseConnector]) -> type[BaseConnector]:
    if cls.name in _registry:
        raise ValueError(f"conector duplicado: {cls.name}")
    _registry[cls.name] = cls
    return cls


def connector_classes() -> dict[str, type[BaseConnector]]:
    return dict(_registry)
