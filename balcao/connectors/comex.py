"""ComexStat (MDIC): o que o Brasil vende e compra do mundo. A API é de
consulta-por-POST com corpo estruturado — e cheia de dialeto próprio: todas
as métricas chegam como STRING, o fluxo é 'export'/'import' em inglês e a
resposta vem embrulhada em data.list. O conector fala português e devolve
Decimal."""

import asyncio
from datetime import date
from decimal import Decimal
from typing import Any

from balcao.connectors.base import BaseConnector, NormalizedResponse, register
from balcao.exceptions import ErroUpstream, ParametroInvalido, RecursoNaoEncontrado
from balcao.models import BalancaMensal, LinhaComercio
from balcao.normalize import limpa_texto

FLUXOS = {"exportacao": "export", "importacao": "import"}

# dimensão amigável -> (detail na fonte, campo do nome na resposta)
DIMENSOES = {
    "pais": ("country", "country"),
    "uf": ("state", "state"),
    "produto": ("chapter", "chapter"),
}

PARAMS_BALANCA = {"de", "ate"}
PARAMS_RANKING = {"fluxo", "de", "ate", "limit"}

FONTE = {
    "nome": "ComexStat — MDIC",
    "url": "https://comexstat.mdic.gov.br",
    "nota": (
        "Estatísticas oficiais de comércio exterior, fechadas mês a mês pela "
        "Secretaria de Comércio Exterior. Valores em dólares FOB."
    ),
}


@register
class ComexConnector(BaseConnector):
    name = "comex"
    base_url = "https://api-comexstat.mdic.gov.br"
    description = "ComexStat (MDIC): balança comercial e rankings de exportação/importação por país, UF e produto"
    resources = {
        "balanca": "exportações, importações e saldo mês a mês (params: de, ate = AAAA-MM)",
        "ranking": (
            "top países, UFs ou produtos de um fluxo; use ranking/pais, ranking/uf ou "
            "ranking/produto (params: fluxo = exportacao|importacao, de, ate, limit)"
        ),
    }

    async def fetch(self, recurso: str, **params: Any) -> NormalizedResponse:
        partes = [p for p in recurso.strip("/").split("/") if p]
        match partes:
            case ["balanca"]:
                return await self._balanca(recurso, params)
            case ["ranking", dimensao] if dimensao in DIMENSOES:
                return await self._ranking(recurso, dimensao, params)
            case _:
                raise RecursoNaoEncontrado(self.name, recurso, sorted(self.resources))

    def _periodo(self, recurso: str, params: dict) -> tuple[str, str]:
        hoje = date.today()
        de = str(params.get("de") or f"{hoje.year}-01")
        ate = str(params.get("ate") or f"{hoje.year}-{hoje.month:02d}")
        for valor in (de, ate):
            pedacos = valor.split("-")
            if len(pedacos) != 2 or not all(p.isdigit() for p in pedacos):
                raise ParametroInvalido(recurso, ["de", "ate"], ["meses no formato AAAA-MM"])
        return de, ate

    async def _consulta(self, corpo: dict) -> list[dict]:
        # o MDIC soluça: responde 200 com success=false de vez em quando e
        # funciona logo em seguida. O retry do transporte não vê isso (não é
        # erro HTTP), então a nova tentativa é daqui — sem ela, o primeiro
        # acesso com cache frio vira 502 na cara do usuário
        ultimo_erro: ErroUpstream | None = None
        for tentativa in range(3):
            if tentativa:
                await asyncio.sleep(0.5 * tentativa)
            bruto = await self.post_json("/general", corpo, timeout=40)
            if isinstance(bruto, dict) and bruto.get("success"):
                return (bruto.get("data") or {}).get("list") or []
            ultimo_erro = ErroUpstream(self.name)
        raise ultimo_erro or ErroUpstream(self.name)

    async def _balanca(self, recurso: str, params: dict) -> NormalizedResponse:
        invalidos = sorted(set(params) - PARAMS_BALANCA)
        if invalidos:
            raise ParametroInvalido(recurso, invalidos, sorted(PARAMS_BALANCA))
        de, ate = self._periodo(recurso, params)

        def corpo(flow: str) -> dict:
            return {
                "flow": flow,
                "monthDetail": True,
                "period": {"from": de, "to": ate},
                "filters": [],
                "details": [],
                "metrics": ["metricFOB"],
            }

        exp, imp = await asyncio.gather(
            self._consulta(corpo("export")), self._consulta(corpo("import"))
        )
        por_mes: dict[str, dict[str, Decimal]] = {}
        for linhas, chave in ((exp, "exportacoes"), (imp, "importacoes")):
            for r in linhas:
                mes = f"{r.get('year')}-{str(r.get('monthNumber')).zfill(2)}"
                por_mes.setdefault(mes, {})[chave] = _decimal(r.get("metricFOB"))

        itens = []
        for mes in sorted(por_mes):
            e = por_mes[mes].get("exportacoes", Decimal(0))
            i = por_mes[mes].get("importacoes", Decimal(0))
            itens.append(
                BalancaMensal(mes=mes, exportacoes=e, importacoes=i, saldo=e - i).model_dump(
                    mode="json"
                )
            )
        meta = {"periodo": f"{de} a {ate}", "moeda": "US$ FOB", "fonte": FONTE}
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=itens, total=len(itens), meta=meta
        )

    async def _ranking(self, recurso: str, dimensao: str, params: dict) -> NormalizedResponse:
        invalidos = sorted(set(params) - PARAMS_RANKING)
        if invalidos:
            raise ParametroInvalido(recurso, invalidos, sorted(PARAMS_RANKING))
        fluxo = str(params.get("fluxo", "exportacao")).lower()
        if fluxo not in FLUXOS:
            raise ParametroInvalido(recurso, ["fluxo"], sorted(FLUXOS))
        limit = params.get("limit", 15)
        if not str(limit).isdigit() or not (1 <= int(limit) <= 100):
            raise ParametroInvalido(recurso, ["limit"], ["1..100"])
        de, ate = self._periodo(recurso, params)

        detail, campo_nome = DIMENSOES[dimensao]
        linhas = await self._consulta(
            {
                "flow": FLUXOS[fluxo],
                "monthDetail": False,
                "period": {"from": de, "to": ate},
                "filters": [],
                "details": [detail],
                "metrics": ["metricFOB", "metricKG"],
            }
        )
        linhas.sort(key=lambda r: _decimal(r.get("metricFOB")), reverse=True)

        itens = [
            LinhaComercio(
                fluxo=fluxo,
                dimensao=dimensao,
                nome=limpa_texto(r.get(campo_nome)),
                codigo=str(r.get("chapterCode")) if r.get("chapterCode") else None,
                valor_fob=_decimal(r.get("metricFOB")),
                peso_kg=_decimal(r.get("metricKG")) if r.get("metricKG") else None,
            ).model_dump(mode="json")
            for r in linhas[: int(limit)]
        ]
        meta = {
            "fluxo": fluxo,
            "periodo": f"{de} a {ate}",
            "moeda": "US$ FOB",
            "total_linhas": len(linhas),
            "fonte": FONTE,
        }
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=itens, total=len(itens), meta=meta
        )


def _decimal(valor: Any) -> Decimal:
    # o ComexStat manda toda métrica como string ("6619343689")
    try:
        return Decimal(str(valor))
    except ArithmeticError:
        return Decimal(0)
