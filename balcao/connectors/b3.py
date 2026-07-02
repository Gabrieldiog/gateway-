"""B3 via brapi.dev: ações e índices da bolsa brasileira. O plano gratuito
tem duas manhas que o conector esconde: só aceita UM ativo por requisição
(então a lista vira fan-out paralelo) e o dado vem com ~15 minutos de
atraso — por isso a fonte É cacheável (TTL padrão), diferente do câmbio.
Token gratuito no .env (BRAPI_TOKEN), header Bearer."""

import asyncio
from decimal import Decimal
from typing import Any

from balcao.config import get_settings
from balcao.connectors.base import BaseConnector, NormalizedResponse, register
from balcao.exceptions import ChaveFaltando, ErroUpstream, ParametroInvalido, RecursoNaoEncontrado
from balcao.models import Acao

# apelido amigável -> símbolo real na fonte
APELIDOS = {"ibov": "^BVSP", "ifix": "IFIX.SA"}
NOMES_INDICE = {"^BVSP": "Ibovespa"}

MAX_TICKERS = 5

FONTE = {
    "nome": "B3 via brapi.dev",
    "url": "https://brapi.dev",
    "nota": (
        "Cotações da bolsa brasileira com ~15 minutos de atraso (plano gratuito "
        "da brapi). Não é preço de execução — pra isso só o home broker."
    ),
}


@register
class B3Connector(BaseConnector):
    name = "b3"
    base_url = "https://brapi.dev/api/v2"
    requires_key = True
    description = "B3 (via brapi): ações e índices da bolsa — IBOV, PETR4, VALE3... (~15 min de atraso)"
    resources = {
        "acoes/{tickers}": f"cotação de até {MAX_TICKERS} ativos separados por vírgula; aceita 'ibov' pro índice",
    }

    def __init__(self, *args, token: str | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._token = token

    @property
    def token(self) -> str:
        if self._token is not None:
            return self._token
        return get_settings().brapi_token

    async def fetch(self, recurso: str, **params: Any) -> NormalizedResponse:
        if not self.token:
            raise ChaveFaltando(self.name, "BRAPI_TOKEN")
        partes = [p for p in recurso.strip("/").split("/") if p]
        match partes:
            case ["acoes", tickers] | ["quote", tickers]:
                return await self._acoes(recurso, tickers, params)
            case _:
                raise RecursoNaoEncontrado(self.name, recurso, sorted(self.resources))

    async def _acoes(self, recurso: str, tickers: str, params: dict) -> NormalizedResponse:
        if params:
            raise ParametroInvalido(recurso, sorted(params), [])
        pedidos = [t.strip() for t in tickers.split(",") if t.strip()]
        if not pedidos or len(pedidos) > MAX_TICKERS:
            raise ParametroInvalido(
                recurso, ["tickers"], [f"1 a {MAX_TICKERS} ativos separados por vírgula"]
            )
        simbolos = [APELIDOS.get(t.lower(), t.upper()) for t in pedidos]

        # o plano gratuito da brapi só aceita 1 ativo por chamada: fan-out
        # paralelo, e um ativo com problema não derruba os outros
        respostas = await asyncio.gather(
            *(self._um(simbolo) for simbolo in simbolos), return_exceptions=True
        )
        itens = []
        indisponiveis = []
        for pedido, simbolo, resp in zip(pedidos, simbolos, respostas):
            if isinstance(resp, ErroUpstream):
                indisponiveis.append(pedido.upper())
                continue
            if isinstance(resp, BaseException):
                raise resp
            if resp is None:
                indisponiveis.append(pedido.upper())
                continue
            itens.append(self._norm(pedido, simbolo, resp).model_dump(mode="json"))

        meta: dict = {"fonte": FONTE, "atraso": "~15 min (plano gratuito)"}
        if indisponiveis:
            meta["indisponiveis"] = indisponiveis
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=itens, total=len(itens), meta=meta
        )

    async def _um(self, simbolo: str) -> dict | None:
        bruto = await self.get_json(
            "/stocks/quote",
            params={"symbols": simbolo},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        resultados = bruto.get("results") if isinstance(bruto, dict) else None
        if not resultados:
            return None
        return resultados[0].get("data") or None

    @staticmethod
    def _norm(pedido: str, simbolo: str, d: dict) -> Acao:
        indice = simbolo.startswith("^")
        ticker = pedido.upper() if simbolo != pedido.upper() else simbolo
        return Acao(
            ticker=ticker,
            nome=NOMES_INDICE.get(simbolo) or d.get("longName") or d.get("shortName"),
            preco=_decimal(d.get("regularMarketPrice")) or Decimal(0),
            variacao_pct=d.get("regularMarketChangePercent"),
            abertura=_decimal(d.get("regularMarketOpen")),
            maxima=_decimal(d.get("regularMarketDayHigh")),
            minima=_decimal(d.get("regularMarketDayLow")),
            fechamento_anterior=_decimal(d.get("regularMarketPreviousClose")),
            moeda=None if indice else d.get("currency"),
            atualizado=d.get("regularMarketTime"),
        )


def _decimal(valor: Any) -> Decimal | None:
    if valor is None:
        return None
    try:
        return Decimal(str(valor))
    except ArithmeticError:
        return None
