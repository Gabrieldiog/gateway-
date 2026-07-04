"""Loterias CAIXA: o resultado de cada jogo, direto da API que abastece o
portal oficial. Não é documentada, mas é JSON limpo e sem chave — um GET por
jogo devolve o último concurso, e /{jogo}/{numero} devolve um específico.
Quirks: valores vêm como float (viram Decimal via str), a data é dd/mm/aaaa,
a Dupla Sena tem segundo sorteio e o Dia de Sorte tem o "Mês da Sorte"."""

from decimal import Decimal
from typing import Any

from balcao.connectors.base import BaseConnector, NormalizedResponse, register
from balcao.exceptions import ErroUpstream, ParametroInvalido, RecursoNaoEncontrado
from balcao.models import SorteioLoteria
from balcao.normalize import limpa_texto, para_data

JOGOS = {
    "megasena": "Mega-Sena",
    "lotofacil": "Lotofácil",
    "quina": "Quina",
    "lotomania": "Lotomania",
    "duplasena": "Dupla Sena",
    "timemania": "Timemania",
    "diadesorte": "Dia de Sorte",
    "supersete": "Super Sete",
    "maismilionaria": "+Milionária",
}

FONTE = {
    "nome": "Loterias CAIXA",
    "url": "https://loterias.caixa.gov.br",
    "nota": (
        "Resultados oficiais dos sorteios, da mesma API que abastece o portal "
        "da CAIXA. Prêmio bruto; a estimativa do próximo concurso é da própria CAIXA."
    ),
}


def _dinheiro(valor: Any) -> Decimal | None:
    if valor in (None, ""):
        return None
    return Decimal(str(valor))


@register
class LoteriasConnector(BaseConnector):
    name = "loterias"
    base_url = "https://servicebus2.caixa.gov.br/portaldeloterias/api"
    description = "Loterias CAIXA: resultado dos sorteios — Mega-Sena, Lotofácil, Quina e os outros"
    resources = {
        "resultado": (
            f"o resultado de um sorteio (params: jogo = {'|'.join(sorted(JOGOS))}, "
            "padrão megasena; concurso = número, padrão o último)"
        ),
    }

    async def fetch(self, recurso: str, **params: Any) -> NormalizedResponse:
        partes = [p for p in recurso.strip("/").split("/") if p]
        match partes:
            case ["resultado"]:
                return await self._resultado(recurso, params)
            case _:
                raise RecursoNaoEncontrado(self.name, recurso, sorted(self.resources))

    async def _resultado(self, recurso: str, params: dict) -> NormalizedResponse:
        invalidos = sorted(set(params) - {"jogo", "concurso"})
        if invalidos:
            raise ParametroInvalido(recurso, invalidos, ["jogo", "concurso"])
        jogo = str(params.get("jogo", "megasena")).lower()
        if jogo not in JOGOS:
            raise ParametroInvalido(recurso, ["jogo"], sorted(JOGOS))
        concurso = str(params.get("concurso", "")).strip()
        if concurso and not concurso.isdigit():
            raise ParametroInvalido(recurso, ["concurso"], ["número do concurso"])

        caminho = f"/{jogo}/{concurso}" if concurso else f"/{jogo}"
        bruto = await self.get_json(caminho, timeout=30)
        if not isinstance(bruto, dict) or not bruto.get("numero"):
            raise ErroUpstream(self.name)

        premios = [
            {
                "faixa": limpa_texto(r.get("descricaoFaixa")) or None,
                "ganhadores": int(r.get("numeroDeGanhadores") or 0),
                "valor": str(_dinheiro(r.get("valorPremio")) or Decimal(0)),
            }
            for r in bruto.get("listaRateioPremio") or []
        ]
        cidades = [
            {
                "municipio": limpa_texto(g.get("municipio")) or None,
                "uf": limpa_texto(g.get("uf")) or None,
                "ganhadores": int(g.get("ganhadores") or 0),
            }
            for g in bruto.get("listaMunicipioUFGanhadores") or []
        ]
        item = SorteioLoteria(
            jogo=jogo,
            nome_jogo=JOGOS[jogo],
            concurso=int(bruto["numero"]),
            data=para_data(bruto.get("dataApuracao")),
            dezenas=[str(d) for d in bruto.get("listaDezenas") or []],
            dezenas_2=[str(d) for d in bruto.get("listaDezenasSegundoSorteio") or []] or None,
            extra=limpa_texto(bruto.get("nomeTimeCoracaoMesSorte")) or None,
            acumulado=bool(bruto.get("acumulado")),
            premios=premios,
            cidades_ganhadoras=cidades,
            arrecadacao=_dinheiro(bruto.get("valorArrecadado")),
            acumulado_proximo=_dinheiro(bruto.get("valorAcumuladoProximoConcurso")),
            estimativa_proximo=_dinheiro(bruto.get("valorEstimadoProximoConcurso")),
            data_proximo=para_data(bruto.get("dataProximoConcurso")),
        ).model_dump(mode="json")

        meta = {"jogo": jogo, "concurso": item["concurso"], "fonte": FONTE}
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=[item], total=1, meta=meta
        )
