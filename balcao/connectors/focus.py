"""Boletim Focus (BACEN): o que o mercado espera pra frente. Enquanto o /serie
do BACEN é retrospectivo (o IPCA que já saiu), o Focus traz a projeção mediana
dos analistas pro ano — atualizada toda semana. A API é OData (plataforma
Olinda): os nomes de recurso são irregulares e o servidor recusa o `$` quando
vem percent-encoded, então a query é montada à mão."""

import asyncio
from datetime import date
from typing import Any
from urllib.parse import quote

from balcao.connectors.base import BaseConnector, NormalizedResponse, register
from balcao.exceptions import ErroUpstream, ParametroInvalido, RecursoNaoEncontrado
from balcao.models import ExpectativaMercado
from balcao.normalize import para_data

# slug amigável -> (nome exato no Focus, unidade)
INDICADORES = {
    "ipca": ("IPCA", "%"),
    "igpm": ("IGP-M", "%"),
    "inpc": ("INPC", "%"),
    "selic": ("Selic", "%"),
    "cambio": ("Câmbio", "R$"),
    "pib": ("PIB Total", "%"),
}

# o painel: o que o mercado espera pro ano, nos indicadores que todos acompanham
PAINEL = ("ipca", "selic", "cambio", "pib", "igpm")

PARAMS = {"ano"}

FONTE = {
    "nome": "Banco Central — Boletim Focus",
    "url": "https://www.bcb.gov.br/publicacoes/focus",
    "nota": (
        "Projeção mediana de mais de cem instituições financeiras, coletada e "
        "divulgada toda semana pelo Banco Central. Expectativa de mercado, não "
        "previsão oficial."
    ),
}


@register
class FocusConnector(BaseConnector):
    name = "focus"
    base_url = "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata"
    description = "Boletim Focus (BACEN): expectativas do mercado pra IPCA, Selic, câmbio, PIB e IGP-M"
    resources = {
        "painel": "o que o mercado espera pro ano: IPCA, Selic, câmbio, PIB e IGP-M (param: ano)",
        **{
            slug: f"expectativa do mercado pra {nome} (param: ano)"
            for slug, (nome, _) in INDICADORES.items()
        },
    }

    async def fetch(self, recurso: str, **params: Any) -> NormalizedResponse:
        partes = [p for p in recurso.strip("/").split("/") if p]
        match partes:
            case ["painel"]:
                return await self._painel(recurso, self._ano(recurso, params))
            case [slug] if slug in INDICADORES:
                return await self._expectativa(recurso, slug, self._ano(recurso, params))
            case _:
                raise RecursoNaoEncontrado(self.name, recurso, sorted(self.resources))

    def _ano(self, recurso: str, params: dict) -> str:
        invalidos = sorted(set(params) - PARAMS)
        if invalidos:
            raise ParametroInvalido(recurso, invalidos, sorted(PARAMS))
        ano = params.get("ano")
        if ano is None:
            # o ano de referência mais consultado é o corrente; o cliente troca via ?ano=
            return str(date.today().year)
        if not str(ano).isdigit():
            raise ParametroInvalido(recurso, ["ano"], sorted(PARAMS))
        return str(int(ano))

    async def _expectativa(self, recurso: str, slug: str, ano: str) -> NormalizedResponse:
        nome, unidade = INDICADORES[slug]
        registro = await self._consulta(nome, ano)
        itens = [self._norm(registro, nome, unidade).model_dump(mode="json")] if registro else []
        meta = {"indicador": nome, "ano": ano, "fonte": FONTE}
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=itens, total=len(itens), meta=meta
        )

    async def _painel(self, recurso: str, ano: str) -> NormalizedResponse:
        async def um(slug: str) -> dict | None:
            nome, unidade = INDICADORES[slug]
            try:
                registro = await self._consulta(nome, ano)
            except ErroUpstream:
                return None
            return self._norm(registro, nome, unidade).model_dump(mode="json") if registro else None

        resultados = await asyncio.gather(*(um(slug) for slug in PAINEL))
        itens = [r for r in resultados if r is not None]
        meta: dict = {"painel": "expectativas do mercado", "fonte": FONTE}
        if ano:
            meta["ano"] = ano
        faltando = [INDICADORES[s][0] for s, r in zip(PAINEL, resultados) if r is None]
        if faltando:
            meta["indisponiveis"] = faltando
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=itens, total=len(itens), meta=meta
        )

    async def _consulta(self, nome_focus: str, ano: str) -> dict | None:
        # baseCalculo 0 = média móvel dos últimos 30 dias; ordena pela coleta e
        # pega a mais recente. O `$` percent-encoded (%24) faz o Olinda devolver
        # 400, então a query vai montada à mão com o cifrão literal.
        filtro = quote(
            f"Indicador eq '{nome_focus}' and DataReferencia eq '{ano}' and baseCalculo eq 0"
        )
        ordem = quote("Data desc")
        path = f"/ExpectativasMercadoAnuais?$format=json&$top=1&$orderby={ordem}&$filter={filtro}"
        bruto = await self.get_json(path)
        valores = bruto.get("value", []) if isinstance(bruto, dict) else []
        return valores[0] if valores else None

    @staticmethod
    def _norm(reg: dict, nome_focus: str, unidade: str) -> ExpectativaMercado:
        return ExpectativaMercado(
            indicador=reg.get("Indicador") or nome_focus,
            referencia=str(reg.get("DataReferencia", "")),
            unidade=unidade,
            data=para_data(reg.get("Data")),
            mediana=reg.get("Mediana"),
            media=reg.get("Media"),
            minimo=reg.get("Minimo"),
            maximo=reg.get("Maximo"),
            desvio_padrao=reg.get("DesvioPadrao"),
            respondentes=reg.get("numeroRespondentes"),
        )
