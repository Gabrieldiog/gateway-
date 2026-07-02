"""DataJud (CNJ): metadados dos processos judiciais do país. A API é um
Elasticsearch cru — um índice por tribunal, query em DSL, resposta enterrada
em hits.hits[]._source — atrás de uma chave PÚBLICA que o próprio CNJ
publica (e rotaciona) na wiki. O conector esconde o Elasticsearch: recebe
tribunal e número, devolve capa normalizada; e transforma agregações no
retrato do que mais se processa."""

from typing import Any

from balcao.config import get_settings
from balcao.connectors.base import BaseConnector, NormalizedResponse, register
from balcao.exceptions import ChaveFaltando, ParametroInvalido, RecursoNaoEncontrado
from balcao.models import ClasseProcessual, Processo
from balcao.normalize import limpa_texto, para_data, so_digitos

PARAMS_PROCESSOS = {"numero", "limit"}

FONTE = {
    "nome": "DataJud — CNJ",
    "url": "https://datajud-wiki.cnj.jus.br/api-publica/",
    "nota": (
        "Base nacional de metadados processuais do Conselho Nacional de Justiça. "
        "Só a capa e as movimentações de processos públicos — partes e conteúdo "
        "não são expostos. A atualização depende de cada tribunal informar o CNJ."
    ),
}


@register
class DatajudConnector(BaseConnector):
    name = "datajud"
    base_url = "https://api-publica.datajud.cnj.jus.br"
    requires_key = True
    description = "DataJud (CNJ): capa e movimentações de processos judiciais por tribunal (tjgo, tjsp, stj, trf1...)"
    resources = {
        "processos/{tribunal}": "consulta processos; params: numero (busca exata) ou limit (mais movimentados recentes)",
        "resumo/{tribunal}": "o que mais se processa: total e as classes mais comuns do tribunal",
    }

    def __init__(self, *args, chave: str | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._chave = chave

    @property
    def chave(self) -> str:
        if self._chave is not None:
            return self._chave
        return get_settings().datajud_api_key

    async def fetch(self, recurso: str, **params: Any) -> NormalizedResponse:
        if not self.chave:
            raise ChaveFaltando(self.name, "DATAJUD_API_KEY")
        partes = [p for p in recurso.strip("/").split("/") if p]
        match partes:
            case ["processos", tribunal]:
                return await self._processos(recurso, self._tribunal(recurso, tribunal), params)
            case ["resumo", tribunal]:
                return await self._resumo(recurso, self._tribunal(recurso, tribunal), params)
            case _:
                raise RecursoNaoEncontrado(self.name, recurso, sorted(self.resources))

    def _tribunal(self, recurso: str, tribunal: str) -> str:
        t = tribunal.strip().lower()
        if not t or not all(c.isalnum() or c == "-" for c in t):
            raise ParametroInvalido(recurso, ["tribunal"], ["sigla como tjgo, tjsp, stj, trf1, tre-sp"])
        return t

    async def _busca(self, tribunal: str, consulta: dict) -> dict:
        # o indice de cada tribunal e um endpoint proprio no Elasticsearch
        return await self.post_json(
            f"/api_publica_{tribunal}/_search",
            consulta,
            timeout=30,
            headers={"Authorization": f"APIKey {self.chave}"},
        )

    async def _processos(self, recurso: str, tribunal: str, params: dict) -> NormalizedResponse:
        invalidos = sorted(set(params) - PARAMS_PROCESSOS)
        if invalidos:
            raise ParametroInvalido(recurso, invalidos, sorted(PARAMS_PROCESSOS))
        numero = so_digitos(str(params.get("numero", "")))
        limit = params.get("limit", 10)
        if not str(limit).isdigit() or not (1 <= int(limit) <= 50):
            raise ParametroInvalido(recurso, ["limit"], ["1..50"])

        if numero:
            consulta: dict = {"size": 5, "query": {"match": {"numeroProcesso": numero}}}
        else:
            # sem numero: os processos movimentados mais recentemente
            consulta = {
                "size": int(limit),
                "query": {"match_all": {}},
                "sort": [{"dataHoraUltimaAtualizacao": {"order": "desc"}}],
            }
        bruto = await self._busca(tribunal, consulta)

        hits = ((bruto.get("hits") or {}).get("hits") or []) if isinstance(bruto, dict) else []
        itens = [self._norm(tribunal, h.get("_source") or {}).model_dump(mode="json") for h in hits]
        meta: dict = {"tribunal": tribunal, "fonte": FONTE}
        if numero:
            meta["numero"] = numero
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=itens, total=len(itens), meta=meta
        )

    async def _resumo(self, recurso: str, tribunal: str, params: dict) -> NormalizedResponse:
        if params:
            raise ParametroInvalido(recurso, sorted(params), [])
        bruto = await self._busca(
            tribunal,
            {
                "size": 0,
                "track_total_hits": True,
                "aggs": {"classes": {"terms": {"field": "classe.nome.keyword", "size": 10}}},
            },
        )
        total = (((bruto.get("hits") or {}).get("total") or {}).get("value")) if isinstance(bruto, dict) else None
        buckets = (
            (((bruto.get("aggregations") or {}).get("classes") or {}).get("buckets") or [])
            if isinstance(bruto, dict)
            else []
        )
        itens = [
            ClasseProcessual(
                tribunal=tribunal, classe=limpa_texto(b.get("key")), processos=int(b.get("doc_count") or 0)
            ).model_dump(mode="json")
            for b in buckets
        ]
        meta = {"tribunal": tribunal, "total_processos": total, "fonte": FONTE}
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=itens, total=len(itens), meta=meta
        )

    @staticmethod
    def _norm(tribunal: str, s: dict) -> Processo:
        classe = s.get("classe") or {}
        orgao = s.get("orgaoJulgador") or {}
        movimentos = s.get("movimentos") or []
        # o ultimo andamento e o de dataHora mais recente, nao o ultimo da lista
        ultimo = max(
            (m for m in movimentos if isinstance(m, dict)),
            key=lambda m: str(m.get("dataHora") or ""),
            default=None,
        )
        return Processo(
            tribunal=tribunal,
            numero=str(s.get("numeroProcesso") or ""),
            classe=limpa_texto(classe.get("nome")) or None,
            assuntos=[
                limpa_texto(a.get("nome"))
                for a in (s.get("assuntos") or [])
                if isinstance(a, dict) and a.get("nome")
            ],
            orgao=limpa_texto(orgao.get("nome")) or None,
            municipio_ibge=orgao.get("codigoMunicipioIBGE"),
            grau=limpa_texto(s.get("grau")) or None,
            ajuizado_em=para_data(s.get("dataAjuizamento")),
            ultima_atualizacao=para_data(s.get("dataHoraUltimaAtualizacao")),
            movimentos=len(movimentos),
            ultimo_movimento=limpa_texto(ultimo.get("nome")) if ultimo else None,
            ultimo_movimento_em=para_data(ultimo.get("dataHora")) if ultimo else None,
        )
