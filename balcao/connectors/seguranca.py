"""Segurança pública: as ocorrências criminais do país pela Base VDE do
Sinesp/MJ. O peso está no arquivo — a leitura e a agregação vivem em
balcao/seguranca.py; aqui ficam a validação, os dois recortes (panorama de
um estado e ranking entre estados) e a normalização final."""

from datetime import date
from typing import Any

from balcao.connectors.base import BaseConnector, NormalizedResponse, register
from balcao.exceptions import ParametroInvalido, RecursoNaoEncontrado
from balcao.models import OcorrenciaSeguranca
from balcao.seguranca import EVENTOS, NOME_UF, POP_UF

FONTE = {
    "nome": "Sinesp — Base de Dados VDE (Ministério da Justiça)",
    "url": "https://www.gov.br/mj/pt-br/acesso-a-informacao/dados-abertos",
    "nota": (
        "Ocorrências informadas pelas polícias estaduais ao Ministério da Justiça, "
        "consolidadas todo mês. Cada estado registra do seu jeito, então a comparação "
        "entre UFs tem ressalvas; a taxa é por 100 mil habitantes (Censo 2022)."
    ),
}


def _ano_padrao() -> int:
    # a base do ano corrente é parcial; o ano fechado é o retrato completo
    return date.today().year - 1


@register
class SegurancaConnector(BaseConnector):
    name = "seguranca"
    base_url = "https://dados.mj.gov.br"
    description = "Sinesp/MJ: ocorrências criminais por estado — homicídio, roubo, feminicídio e mais"
    # o dado sai de um arquivo file-backed (ArquivosSeguranca), não do get_json
    resources = {
        "panorama": (
            "todos os crimes de um estado num ano, do mais ao menos frequente "
            f"(params: uf obrigatória; ano, padrão {_ano_padrao()})"
        ),
        "ranking": (
            "um crime comparado entre os 27 estados, por 100 mil habitantes "
            f"(params: crime = {'|'.join(list(EVENTOS)[:5])}...; ano, padrão {_ano_padrao()})"
        ),
    }

    def __init__(self, *args, arquivos=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._arquivos = arquivos  # injetado pelo lifespan; nos testes, um fake

    async def fetch(self, recurso: str, **params: Any) -> NormalizedResponse:
        partes = [p for p in recurso.strip("/").split("/") if p]
        match partes:
            case ["panorama"]:
                return await self._panorama(recurso, params)
            case ["ranking"]:
                return await self._ranking(recurso, params)
            case _:
                raise RecursoNaoEncontrado(self.name, recurso, sorted(self.resources))

    def _ano(self, recurso: str, params: dict) -> int:
        ano = str(params.get("ano", "")).strip()
        if not ano:
            return _ano_padrao()
        if not ano.isdigit() or not (2015 <= int(ano) <= date.today().year):
            raise ParametroInvalido(recurso, ["ano"], [f"2015..{date.today().year}"])
        return int(ano)

    async def _panorama(self, recurso: str, params: dict) -> NormalizedResponse:
        invalidos = sorted(set(params) - {"uf", "ano"})
        if invalidos:
            raise ParametroInvalido(recurso, invalidos, ["uf", "ano"])
        uf = str(params.get("uf", "")).strip().upper()
        if uf not in POP_UF:
            raise ParametroInvalido(recurso, ["uf"], ["sigla de UF (obrigatória)"])
        ano = self._ano(recurso, params)

        indice = await self._arquivos.indice(ano)
        do_estado = indice.get(uf, {})
        itens = []
        for slug, label in EVENTOS.items():
            ag = do_estado.get(slug)
            if ag is None:
                continue
            vitima = ag.feminino + ag.masculino > 0
            meses = [{"mes": m, "total": ag.meses[m]} for m in sorted(ag.meses)]
            itens.append(
                OcorrenciaSeguranca(
                    ano=ano, uf=uf, local=NOME_UF[uf], evento=label, total=ag.total,
                    feminino=ag.feminino if vitima else None,
                    masculino=ag.masculino if vitima else None,
                    meses=meses or None,
                ).model_dump(mode="json")
            )
        itens.sort(key=lambda i: i["total"], reverse=True)
        meta = {"uf": uf, "ano": ano, "ano_automatico": "ano" not in params, "fonte": FONTE}
        return NormalizedResponse(fonte=self.name, recurso=recurso, dados=itens, total=len(itens), meta=meta)

    async def _ranking(self, recurso: str, params: dict) -> NormalizedResponse:
        invalidos = sorted(set(params) - {"crime", "ano"})
        if invalidos:
            raise ParametroInvalido(recurso, invalidos, ["crime", "ano"])
        crime = str(params.get("crime", "homicidio")).lower()
        if crime not in EVENTOS:
            raise ParametroInvalido(recurso, ["crime"], sorted(EVENTOS))
        ano = self._ano(recurso, params)

        indice = await self._arquivos.indice(ano)
        itens = []
        for uf, pop in POP_UF.items():
            ag = indice.get(uf, {}).get(crime)
            if ag is None:
                continue
            itens.append(
                OcorrenciaSeguranca(
                    ano=ano, uf=uf, local=NOME_UF[uf], evento=EVENTOS[crime],
                    total=ag.total, por_100k=round(ag.total / pop * 100000, 1),
                ).model_dump(mode="json")
            )
        itens.sort(key=lambda i: i["por_100k"] or 0, reverse=True)
        meta = {"crime": crime, "ano": ano, "ano_automatico": "ano" not in params, "fonte": FONTE}
        return NormalizedResponse(fonte=self.name, recurso=recurso, dados=itens, total=len(itens), meta=meta)
