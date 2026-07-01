import asyncio
from decimal import Decimal, InvalidOperation
from typing import Any

from pydantic import ValidationError

from balcao.connectors.base import BaseConnector, NormalizedResponse, register
from balcao.exceptions import ErroUpstream, ParametroInvalido, RecursoNaoEncontrado
from balcao.models import IndicadorEconomico, PontoSerie
from balcao.normalize import data_br, para_data

# atalhos pros codigos de serie mais pedidos do SGS
SERIES = {
    "selic": 432,
    "cdi": 12,
    "ipca": 433,
    "ipca12m": 13522,  # IPCA acumulado em 12 meses
    "inpc": 188,
    "igpm": 189,
    "igpdi": 190,
    "poupanca": 196,  # rendimento mensal; a 195 é o índice diário de aniversário
    "dolar": 1,
    "euro": 21619,
}

# rótulo e unidade de cada série, usados só no painel de custo de vida
INDICADORES = {
    "ipca": ("IPCA (mês)", "% no mês"),
    "ipca12m": ("IPCA (12 meses)", "% ao ano"),
    "inpc": ("INPC (mês)", "% no mês"),
    "igpm": ("IGP-M (mês)", "% no mês"),
    "igpdi": ("IGP-DI (mês)", "% no mês"),
    "selic": ("Selic (meta)", "% ao ano"),
    "cdi": ("CDI", "% ao dia"),
    "poupanca": ("Poupança", "% no mês"),
    "dolar": ("Dólar (PTAX)", "R$"),
    "euro": ("Euro (PTAX)", "R$"),
}

# o painel "custo de vida": os indicadores que pesam no bolso, na ordem de exibição
PAINEL = ("ipca12m", "ipca", "igpm", "inpc", "selic", "cdi", "poupanca", "dolar")

PARAMS_SERIE = {"data_inicio", "data_fim", "ultimos"}


@register
class BacenConnector(BaseConnector):
    name = "bacen"
    base_url = "https://api.bcb.gov.br/dados/serie"
    description = "Banco Central (SGS): Selic, CDI, IPCA, IGP-M, câmbio e mais de 190 séries econômicas"
    suporta_busca = True
    resources = {
        "inflacao": "painel de custo de vida: IPCA, IGP-M, INPC, Selic, CDI, poupança e dólar (valor mais recente)",
        "serie/{codigo}": f"pontos de uma série do SGS; filtros: {', '.join(sorted(PARAMS_SERIE))}",
        **{
            apelido: f"atalho pra série {codigo} do SGS"
            for apelido, codigo in SERIES.items()
        },
    }

    async def fetch(self, recurso: str, **params: Any) -> NormalizedResponse:
        partes = [p for p in recurso.strip("/").split("/") if p]
        match partes:
            case ["inflacao"] | ["painel"]:
                return await self._painel(recurso)
            case [apelido] if apelido in SERIES:
                return await self._serie(recurso, SERIES[apelido], params, nome=apelido)
            case ["serie", codigo] if codigo.isdigit():
                return await self._serie(recurso, int(codigo), params)
            case _:
                raise RecursoNaoEncontrado(self.name, recurso, sorted(self.resources))

    async def buscar(self, q: str) -> list[dict]:
        termo = q.casefold()
        achados = []
        for apelido, codigo in SERIES.items():
            if termo in apelido:
                resposta = await self._serie(apelido, codigo, {"ultimos": "5"}, nome=apelido)
                achados += [
                    {"tipo_resultado": "serie_economica", **p} for p in resposta.dados
                ]
        return achados

    async def _painel(self, recurso: str) -> NormalizedResponse:
        """Junta o valor mais recente dos indicadores que pesam no bolso numa
        resposta só. Dispara as séries em paralelo; se uma fonte falhar, o
        painel volta sem ela em vez de morrer."""

        async def ultimo(chave: str) -> dict | None:
            codigo = SERIES[chave]
            nome, unidade = INDICADORES[chave]
            try:
                resp = await self._serie(chave, codigo, {"ultimos": "1"}, nome=nome)
            except ErroUpstream:
                return None
            if not resp.dados:
                return None
            ponto = resp.dados[-1]
            return IndicadorEconomico(
                chave=chave,
                serie=codigo,
                nome=nome,
                unidade=unidade,
                data=ponto["data"],
                valor=Decimal(str(ponto["valor"])),
            ).model_dump(mode="json")

        resultados = await asyncio.gather(*(ultimo(chave) for chave in PAINEL))
        itens = [r for r in resultados if r is not None]
        meta: dict = {"painel": "custo de vida"}
        faltando = [c for c, r in zip(PAINEL, resultados) if r is None]
        if faltando:
            meta["indisponiveis"] = faltando
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=itens, total=len(itens), meta=meta
        )

    async def _serie(
        self, recurso: str, codigo: int, params: dict, nome: str | None = None
    ) -> NormalizedResponse:
        invalidos = sorted(set(params) - PARAMS_SERIE)
        if invalidos:
            raise ParametroInvalido(recurso, invalidos, sorted(PARAMS_SERIE))

        ultimos = str(params.get("ultimos", ""))
        if ultimos and not ultimos.isdigit():
            raise ParametroInvalido(recurso, ["ultimos"], sorted(PARAMS_SERIE))

        if ultimos:
            path = f"/bcdata.sgs.{codigo}/dados/ultimos/{int(ultimos)}"
            query = {"formato": "json"}
        elif "data_inicio" in params or "data_fim" in params:
            # o SGS quer datas em dd/mm/aaaa; o Balcao aceita ISO e traduz
            query = {"formato": "json"}
            for chave, alvo in (("data_inicio", "dataInicial"), ("data_fim", "dataFinal")):
                if chave in params:
                    valor = data_br(params[chave])
                    if valor is None:
                        raise ParametroInvalido(recurso, [chave], sorted(PARAMS_SERIE))
                    query[alvo] = valor
            path = f"/bcdata.sgs.{codigo}/dados"
        else:
            # sem recorte a serie inteira viria com decadas de pontos
            path = f"/bcdata.sgs.{codigo}/dados/ultimos/20"
            query = {"formato": "json"}

        bruto = await self.get_json(path, params=query)

        # o SGS às vezes devolve {"erro": {...}} com HTTP 200 (ex.: ultimos/1 em
        # série de índice diário); trata como vazio em vez de estourar no laço
        if not isinstance(bruto, list):
            bruto = []

        itens = []
        descartados = 0
        for b in bruto:
            try:
                ponto = PontoSerie(
                    serie=codigo,
                    nome=nome,
                    data=para_data(b.get("data")),
                    valor=Decimal(str(b.get("valor"))),
                )
                itens.append(ponto.model_dump(mode="json"))
            except (ValidationError, KeyError, InvalidOperation):
                descartados += 1

        meta: dict = {"serie": codigo}
        if descartados:
            meta["descartados"] = descartados
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=itens, total=len(itens), meta=meta
        )
