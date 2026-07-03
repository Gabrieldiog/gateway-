"""Obrasgov.br (Ministério da Gestão): o cadastro nacional de obras e
projetos de investimento federais — incluindo as paralisadas, que são a
pauta. Quirks da fonte: a paginação começa em 0, o totalElements MENTE
(devolve o tamanho da página, não o total), e o valor previsto vem vazio
com frequência — usamos o campo `last` pra paginar e declaramos o vazio."""

from datetime import date
from decimal import Decimal
from typing import Any

from balcao.connectors.base import BaseConnector, NormalizedResponse, register
from balcao.exceptions import ParametroInvalido, RecursoNaoEncontrado
from balcao.models import ObraPublica
from balcao.normalize import limpa_texto, normaliza_uf, para_data

FONTE = {
    "nome": "Obrasgov.br — Ministério da Gestão e da Inovação",
    "url": "https://obrasgov.gestao.gov.br",
    "nota": (
        "O cadastro oficial de obras e projetos de investimento com recursos "
        "federais — situação, valores e datas previstas, obra a obra."
    ),
}

SITUACOES = {
    "paralisada": "Paralisada",
    "execucao": "Em Execução",
    "concluida": "Concluída",
    "cadastrada": "Cadastrada",
    "cancelada": "Cancelada",
}

TERMINADAS = {"Concluída", "Cancelada"}


def _int_ou_none(v: Any) -> int | None:
    # a fonte manda "" onde deveria ser null — coercao defensiva
    s = str(v if v is not None else "").strip()
    return int(s) if s.isdigit() else None


@register
class ObrasgovConnector(BaseConnector):
    name = "obrasgov"
    base_url = "https://api.obrasgov.gestao.gov.br/obrasgov/api"
    description = "Obrasgov: obras federais com situação, valores e datas — inclusive as paralisadas"
    resources = {
        "obras": (
            "obras e projetos de investimento federais "
            f"(params: uf, situacao = {', '.join(sorted(SITUACOES))}, pagina)"
        ),
    }

    async def fetch(self, recurso: str, **params: Any) -> NormalizedResponse:
        partes = [p for p in recurso.strip("/").split("/") if p]
        match partes:
            case ["obras"]:
                return await self._obras(recurso, params)
            case _:
                raise RecursoNaoEncontrado(self.name, recurso, sorted(self.resources))

    async def _obras(self, recurso: str, params: dict) -> NormalizedResponse:
        aceitos = {"uf", "situacao", "pagina"}
        invalidos = sorted(set(params) - aceitos)
        if invalidos:
            raise ParametroInvalido(recurso, invalidos, sorted(aceitos))
        pagina = str(params.get("pagina", 1))
        if not pagina.isdigit() or int(pagina) < 1:
            raise ParametroInvalido(recurso, ["pagina"], ["pagina >= 1"])
        # a fonte pagina do zero; o Balcão fala em página 1 como as demais
        consulta: dict = {"pagina": int(pagina) - 1, "tamanhoDaPagina": 20}
        if params.get("uf"):
            uf = normaliza_uf(params["uf"])
            if uf is None:
                raise ParametroInvalido(recurso, ["uf"], ["sigla de UF"])
            consulta["uf"] = uf
        situacao = str(params.get("situacao", "")).strip().lower()
        if situacao:
            if situacao not in SITUACOES:
                raise ParametroInvalido(recurso, [f"situacao={situacao}"], sorted(SITUACOES))
            consulta["situacao"] = SITUACOES[situacao]

        bruto = await self.get_json("/projeto-investimento", params=consulta, timeout=40)
        hoje = date.today()
        itens = []
        for o in bruto.get("content", []) if isinstance(bruto, dict) else []:
            fim_previsto = para_data(o.get("dataFinalPrevista"))
            sit = limpa_texto(o.get("situacao")) or None
            valor = o.get("valorInvestimentoPrevisto")
            itens.append(
                ObraPublica(
                    id=str(o.get("idUnico") or ""),
                    nome=limpa_texto(o.get("nome")) or "—",
                    descricao=limpa_texto(o.get("descricao")) or None,
                    uf=o.get("uf") or None,
                    endereco=limpa_texto(o.get("endereco")) or None,
                    situacao=sit,
                    especie=limpa_texto(o.get("especie")) or None,
                    valor_previsto=Decimal(str(valor)) if valor not in (None, "") else None,
                    inicio_previsto=para_data(o.get("dataInicialPrevista")),
                    fim_previsto=fim_previsto,
                    inicio_efetivo=para_data(o.get("dataInicialEfetiva")),
                    fim_efetivo=para_data(o.get("dataFinalEfetiva")),
                    empregos=_int_ou_none(o.get("qdtEmpregosGerados")),
                    populacao_beneficiada=_int_ou_none(o.get("populacaoBeneficiada")),
                    atrasada=bool(
                        fim_previsto and fim_previsto < hoje and (sit or "") not in TERMINADAS
                    ),
                ).model_dump(mode="json")
            )
        meta = {
            "pagina": int(pagina),
            # totalElements da fonte mente; o `last` é confiável
            "tem_proxima": not bool(bruto.get("last", True)) if isinstance(bruto, dict) else False,
            "situacao": SITUACOES.get(situacao) or "todas",
            "fonte": FONTE,
        }
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=itens, total=len(itens), meta=meta
        )
