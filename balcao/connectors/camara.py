from typing import Any

from balcao.connectors.base import BaseConnector, NormalizedResponse, register


@register
class CamaraConnector(BaseConnector):
    name = "camara"
    base_url = "https://dadosabertos.camara.leg.br/api/v2"
    description = "Câmara dos Deputados: deputados, despesas (CEAP), votações e proposições"

    async def fetch(self, recurso: str, **params: Any) -> NormalizedResponse:
        # os recursos de verdade entram no TICKET-03, aqui e so o esqueleto registravel
        raise NotImplementedError("recursos da Camara serao implementados no TICKET-03")
