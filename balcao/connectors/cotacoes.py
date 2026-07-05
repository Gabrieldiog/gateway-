import re
from decimal import Decimal, InvalidOperation
from typing import Any

from pydantic import ValidationError

from balcao.connectors.base import BaseConnector, NormalizedResponse, register
from balcao.exceptions import ParametroInvalido, RecursoNaoEncontrado
from balcao.models import Cotacao

# um ou mais pares separados por vírgula: USD-BRL,EUR-BRL,BTC-BRL
PARES = re.compile(r"^[A-Za-z]{3,4}-[A-Za-z]{3,4}(,[A-Za-z]{3,4}-[A-Za-z]{3,4})*$")


@register
class CotacoesConnector(BaseConnector):
    name = "cotacoes"
    base_url = "https://economia.awesomeapi.com.br/json"
    description = "Cotações de câmbio e cripto quase em tempo real (preço de mercado), via AwesomeAPI"
    # cache curto (cache_vivo_ttl): a AwesomeAPI rate-limita (429) um IP fixo que
    # busca a cada request; com o /pulso fazendo polling, um cache de segundos
    # segura a fonte no lugar. O valor ainda é "ao vivo" pro leitor.
    tempo_real = True
    resources = {
        "last/{pares}": "cotação atual de um ou mais pares, ex: USD-BRL,EUR-BRL,BTC-BRL",
    }

    async def fetch(self, recurso: str, **params: Any) -> NormalizedResponse:
        partes = [p for p in recurso.strip("/").split("/") if p]
        match partes:
            case ["last", pares]:
                return await self._last(recurso, pares)
            case _:
                raise RecursoNaoEncontrado(self.name, recurso, sorted(self.resources))

    async def _last(self, recurso: str, pares: str) -> NormalizedResponse:
        if not PARES.match(pares):
            raise ParametroInvalido(recurso, [f"pares={pares}"], ["ex: USD-BRL,EUR-BRL,BTC-BRL"])
        bruto = await self.get_json(f"/last/{pares.upper()}")
        cotacoes: list[dict] = []
        # a AwesomeAPI devolve um dict {"USDBRL": {...}, "EURBRL": {...}}
        for v in (bruto or {}).values():
            try:
                cotacoes.append(self._norm(v).model_dump(mode="json"))
            except (ValidationError, InvalidOperation, KeyError, TypeError):
                continue
        return NormalizedResponse(fonte=self.name, recurso=recurso, dados=cotacoes, total=len(cotacoes))

    @staticmethod
    def _norm(v: dict) -> Cotacao:
        def dec(x: Any) -> Decimal | None:
            return Decimal(str(x)) if x not in (None, "") else None

        return Cotacao(
            par=f"{v['code']}/{v['codein']}",
            moeda=v["code"],
            nome=v.get("name"),
            compra=Decimal(str(v["bid"])),
            venda=dec(v.get("ask")),
            variacao_pct=float(v["pctChange"]) if v.get("pctChange") not in (None, "") else None,
            maxima=dec(v.get("high")),
            minima=dec(v.get("low")),
            atualizado=v.get("create_date"),
        )
