"""Obrasgov.br (Ministério da Gestão): o cadastro nacional de obras e
projetos de investimento federais, incluindo as paralisadas, que são a
pauta. Quirks da fonte: a paginação começa em 0, o totalElements MENTE
(devolve o tamanho da página, não o total), e o valor previsto vem vazio
com frequência, usamos o campo `last` pra paginar e declaramos o vazio."""

from datetime import date
from decimal import Decimal
from typing import Any

from balcao.connectors.base import BaseConnector, NormalizedResponse, register
from balcao.exceptions import ErroUpstream, ParametroInvalido, RecursoNaoEncontrado
from balcao.models import EmpenhoObra, ObraPublica
from balcao.normalize import limpa_texto, normaliza_uf, para_data

FONTE = {
    "nome": "Obrasgov.br, Ministério da Gestão e da Inovação",
    "url": "https://www.gov.br/obrasgov/pt-br",
    "nota": (
        "O cadastro oficial de obras e projetos de investimento com recursos "
        "federais, situação, valores e datas previstas, obra a obra."
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
    # a fonte manda "" onde deveria ser null, coercao defensiva
    s = str(v if v is not None else "").strip()
    return int(s) if s.isdigit() else None


# a fonte usa R$ 0,01 como marcador de "sem valor" em algumas obras (FNDE)
PLACEHOLDER = Decimal("0.01")


@register
class ObrasgovConnector(BaseConnector):
    name = "obrasgov"
    base_url = "https://api.obrasgov.gestao.gov.br/obrasgov/api"
    description = "Obrasgov: obras federais com situação, valores e datas; inclusive as paralisadas"
    resources = {
        "obras": (
            "obras e projetos de investimento federais "
            f"(params: uf, situacao = {', '.join(sorted(SITUACOES))}, pagina; ou id = idUnico)"
        ),
        "execucao": "os empenhos de uma obra, o dinheiro que já saiu (params: id = idUnico, pagina)",
    }

    async def fetch(self, recurso: str, **params: Any) -> NormalizedResponse:
        partes = [p for p in recurso.strip("/").split("/") if p]
        match partes:
            case ["obras"]:
                return await self._obras(recurso, params)
            case ["execucao"]:
                return await self._execucao(recurso, params)
            case _:
                raise RecursoNaoEncontrado(self.name, recurso, sorted(self.resources))

    @staticmethod
    def _valor_previsto(o: dict) -> Decimal | None:
        """O valor NAO mora no top-level (vem sempre null): a verdade esta em
        fontesDeRecurso[].valorInvestimentoPrevisto, somando as origens
        (Federal/Estadual/...). R$ 0,01 e marcador de vazio; vira None."""
        total = Decimal(0)
        for f in o.get("fontesDeRecurso") or []:
            v = f.get("valorInvestimentoPrevisto")
            if v not in (None, ""):
                total += Decimal(str(v))
        if total <= PLACEHOLDER:
            topo = o.get("valorInvestimentoPrevisto")
            if topo not in (None, ""):
                total = Decimal(str(topo))
        return total if total > PLACEHOLDER else None

    async def _execucao(self, recurso: str, params: dict) -> NormalizedResponse:
        """O dinheiro que ja saiu: os empenhos da obra. Quirks da fonte:
        o filtro e idProjetoInvestimento (= idUnico) e obra sem empenho
        responde HTTP 404, aqui isso vira lista vazia, nao erro."""
        aceitos = {"id", "pagina"}
        invalidos = sorted(set(params) - aceitos)
        if invalidos:
            raise ParametroInvalido(recurso, invalidos, sorted(aceitos))
        id_obra = str(params.get("id", "")).strip()
        if not id_obra:
            raise ParametroInvalido(recurso, ["id"], ["id = idUnico da obra (ex 33266.16-49)"])
        pagina = str(params.get("pagina", 1))
        if not pagina.isdigit() or int(pagina) < 1:
            raise ParametroInvalido(recurso, ["pagina"], ["pagina >= 1"])
        tamanho = 50
        try:
            bruto = await self.get_json(
                "/execucao-financeira",
                params={
                    "idProjetoInvestimento": id_obra,
                    "pagina": int(pagina) - 1,
                    "tamanhoDaPagina": tamanho,
                },
                timeout=40,
            )
        except ErroUpstream as exc:
            if exc.status_code != 404:
                raise
            bruto = {"content": []}
        itens = []
        total = Decimal(0)
        for e in bruto.get("content", []) if isinstance(bruto, dict) else []:
            valor = e.get("valorEmpenho")
            dec = Decimal(str(valor)) if valor not in (None, "") else None
            if dec:
                total += dec
            itens.append(
                EmpenhoObra(
                    obra=id_obra,
                    favorecido=limpa_texto(e.get("nomeFavorecido")) or None,
                    valor=dec,
                    natureza=limpa_texto(e.get("naturezaDespesa")) or None,
                    nota=limpa_texto(e.get("numeroNotaEmpenhoGerada")) or None,
                    ug=str(e.get("ugEmitente") or "") or None,
                ).model_dump(mode="json")
            )
        meta = {
            "obra": id_obra,
            "pagina": int(pagina),
            "tem_proxima": len(itens) == tamanho,
            "total_empenhado_na_pagina": str(total),
            "fonte": FONTE,
        }
        if not itens:
            meta["aviso"] = "nenhum empenho registrado pra esta obra"
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=itens, total=len(itens), meta=meta
        )

    async def _obras(self, recurso: str, params: dict) -> NormalizedResponse:
        aceitos = {"uf", "situacao", "pagina", "id"}
        invalidos = sorted(set(params) - aceitos)
        if invalidos:
            raise ParametroInvalido(recurso, invalidos, sorted(aceitos))
        pagina = str(params.get("pagina", 1))
        if not pagina.isdigit() or int(pagina) < 1:
            raise ParametroInvalido(recurso, ["pagina"], ["pagina >= 1"])
        # a fonte pagina do zero; o Balcão fala em página 1 como as demais
        tamanho = 20
        consulta: dict = {"pagina": int(pagina) - 1, "tamanhoDaPagina": tamanho}
        if params.get("id"):
            consulta["idUnico"] = str(params["id"]).strip()
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
            valor = self._valor_previsto(o)
            executor = (o.get("executores") or [{}])[0] or {}
            itens.append(
                ObraPublica(
                    id=str(o.get("idUnico") or ""),
                    nome=limpa_texto(o.get("nome")) or "sem dado",
                    descricao=limpa_texto(o.get("descricao")) or None,
                    uf=o.get("uf") or None,
                    endereco=limpa_texto(o.get("endereco")) or None,
                    situacao=sit,
                    especie=limpa_texto(o.get("especie")) or None,
                    valor_previsto=valor,
                    inicio_previsto=para_data(o.get("dataInicialPrevista")),
                    fim_previsto=fim_previsto,
                    inicio_efetivo=para_data(o.get("dataInicialEfetiva")),
                    fim_efetivo=para_data(o.get("dataFinalEfetiva")),
                    executor=limpa_texto(executor.get("nome")) or None,
                    executor_codigo=str(executor.get("codigo") or "") or None,
                    empregos=_int_ou_none(o.get("qdtEmpregosGerados")),
                    populacao_beneficiada=_int_ou_none(o.get("populacaoBeneficiada")),
                    atrasada=bool(
                        fim_previsto and fim_previsto < hoje and (sit or "") not in TERMINADAS
                    ),
                ).model_dump(mode="json")
            )
        meta = {
            "pagina": int(pagina),
            # os metadados de paginacao da fonte MENTEM (last=true em toda
            # pagina, totalPages = pagina+1); pagina cheia e o unico sinal
            # confiavel de que ha proxima
            "tem_proxima": len(itens) == tamanho,
            "situacao": SITUACOES.get(situacao) or "todas",
            "fonte": FONTE,
        }
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=itens, total=len(itens), meta=meta
        )
