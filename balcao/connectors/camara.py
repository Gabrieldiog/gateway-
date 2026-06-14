import asyncio
from decimal import Decimal, InvalidOperation
from typing import Any

from pydantic import ValidationError

from balcao.connectors.base import BaseConnector, NormalizedResponse, register
from balcao.exceptions import ParametroInvalido, RecursoNaoEncontrado
from balcao.models import Deputado, Despesa, Proposicao, Votacao, VotoDeputado
from balcao.normalize import limpa_texto, normaliza_uf, para_data, so_digitos

# de um lado os nomes genericos do Balcao, do outro os que a Camara espera
PARAMS_DEPUTADOS = {
    "uf": "siglaUf",
    "partido": "siglaPartido",
    "nome": "nome",
    "legislatura": "idLegislatura",
    "pagina": "pagina",
    "itens": "itens",
}
PARAMS_DESPESAS = {
    "ano": "ano",
    "mes": "mes",
    "fornecedor_doc": "cnpjCpfFornecedor",
    "pagina": "pagina",
    "itens": "itens",
}
PARAMS_VOTACOES = {
    "proposicao": "idProposicao",
    "evento": "idEvento",
    "orgao": "idOrgao",
    "data_inicio": "dataInicio",
    "data_fim": "dataFim",
    "pagina": "pagina",
    "itens": "itens",
}
PARAMS_PROPOSICOES = {
    "tipo": "siglaTipo",
    "numero": "numero",
    "ano": "ano",
    "autor": "autor",
    "partido_autor": "siglaPartidoAutor",
    "busca": "keywords",
    "data_inicio": "dataInicio",
    "data_fim": "dataFim",
    "pagina": "pagina",
    "itens": "itens",
}


@register
class CamaraConnector(BaseConnector):
    name = "camara"
    base_url = "https://dadosabertos.camara.leg.br/api/v2"
    description = "Câmara dos Deputados: deputados, despesas (CEAP), votações e proposições"
    suporta_busca = True
    resources = {
        "deputados": f"lista deputados; filtros: {', '.join(PARAMS_DEPUTADOS)}",
        "deputados/{id}": "detalhe de um deputado",
        "deputados/{id}/despesas": f"despesas CEAP; filtros: {', '.join(PARAMS_DESPESAS)}",
        "votacoes": f"votações; filtros: {', '.join(PARAMS_VOTACOES)}",
        "votacoes/{id}": "detalhe de uma votação (placar, data, órgão)",
        "votacoes/{id}/votos": "voto de cada deputado (Sim/Não/Abstenção); só votação nominal tem",
        "proposicoes": f"proposições; filtros: {', '.join(PARAMS_PROPOSICOES)}",
    }

    async def fetch(self, recurso: str, **params: Any) -> NormalizedResponse:
        partes = [p for p in recurso.strip("/").split("/") if p]
        match partes:
            case ["deputados"]:
                return await self._deputados(recurso, params)
            case ["deputados", dep_id] if dep_id.isdigit():
                return await self._deputado_detalhe(recurso, int(dep_id))
            case ["deputados", dep_id, "despesas"] if dep_id.isdigit():
                return await self._despesas(recurso, int(dep_id), params)
            case ["votacoes"]:
                return await self._votacoes(recurso, params)
            case ["votacoes", vid, "votos"]:  # id tem hífen ("2629954-8"), não é só dígito
                return await self._votos(recurso, vid)
            case ["votacoes", vid]:
                return await self._votacao_detalhe(recurso, vid)
            case ["proposicoes"]:
                return await self._proposicoes(recurso, params)
            case _:
                raise RecursoNaoEncontrado(self.name, recurso, sorted(self.resources))

    async def buscar(self, q: str) -> list[dict]:
        # deputados por nome e proposicoes por palavra-chave, em paralelo
        deputados, proposicoes = await asyncio.gather(
            self.get_json("/deputados", params={"nome": q, "itens": 10}),
            self.get_json("/proposicoes", params={"keywords": q, "itens": 10}),
        )
        achados = []
        for b in deputados.get("dados", []):
            achados.append(
                {"tipo_resultado": "deputado", **self._norm_deputado(b).model_dump(mode="json")}
            )
        for b in proposicoes.get("dados", []):
            achados.append(
                {"tipo_resultado": "proposicao", **self._norm_proposicao(b).model_dump(mode="json")}
            )
        return achados

    async def _deputados(self, recurso: str, params: dict) -> NormalizedResponse:
        query = self._traduz(recurso, params, PARAMS_DEPUTADOS)
        bruto = await self.get_json("/deputados", params=query)
        return self._envelopa(recurso, bruto, params, self._norm_deputado)

    async def _deputado_detalhe(self, recurso: str, dep_id: int) -> NormalizedResponse:
        bruto = await self.get_json(f"/deputados/{dep_id}")
        dado = bruto.get("dados", {})
        # o detalhe vem num shape proprio, com o essencial dentro de ultimoStatus
        status = dado.get("ultimoStatus", {})
        deputado = Deputado(
            id=dado["id"],
            nome=limpa_texto(status.get("nome") or dado.get("nomeCivil")),
            partido=status.get("siglaPartido"),
            uf=normaliza_uf(status.get("siglaUf")),
            legislatura=status.get("idLegislatura"),
            email=status.get("email") or dado.get("email"),
            foto=status.get("urlFoto"),
            situacao=status.get("situacao"),
        )
        return NormalizedResponse(
            fonte=self.name,
            recurso=recurso,
            dados=[deputado.model_dump(mode="json")],
            total=1,
        )

    async def _despesas(self, recurso: str, dep_id: int, params: dict) -> NormalizedResponse:
        query = self._traduz(recurso, params, PARAMS_DESPESAS)
        bruto = await self.get_json(f"/deputados/{dep_id}/despesas", params=query)
        return self._envelopa(
            recurso, bruto, params, lambda b: self._norm_despesa(b, dep_id)
        )

    async def _votacoes(self, recurso: str, params: dict) -> NormalizedResponse:
        query = self._traduz(recurso, params, PARAMS_VOTACOES)
        bruto = await self.get_json("/votacoes", params=query)
        return self._envelopa(recurso, bruto, params, self._norm_votacao)

    async def _votacao_detalhe(self, recurso: str, vid: str) -> NormalizedResponse:
        bruto = await self.get_json(f"/votacoes/{vid}")
        dado = bruto.get("dados", {})
        return NormalizedResponse(
            fonte=self.name,
            recurso=recurso,
            dados=[self._norm_votacao(dado).model_dump(mode="json")],
            total=1,
        )

    async def _votos(self, recurso: str, vid: str) -> NormalizedResponse:
        bruto = await self.get_json(f"/votacoes/{vid}/votos")
        itens, descartados = [], 0
        placar: dict[str, int] = {}
        for v in bruto.get("dados", []):
            try:
                voto = self._norm_voto(v, vid)
            except (ValidationError, KeyError):
                descartados += 1
                continue
            itens.append(voto.model_dump(mode="json"))
            placar[voto.voto] = placar.get(voto.voto, 0) + 1
        meta: dict[str, Any] = {}
        if placar:
            meta["placar"] = placar
        else:
            # votação simbólica é aprovada "de viva voz" e não guarda voto por deputado
            meta["aviso"] = "votação simbólica não registra voto por deputado; só as nominais têm"
        if descartados:
            meta["descartados"] = descartados
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=itens, total=len(itens), meta=meta
        )

    async def _proposicoes(self, recurso: str, params: dict) -> NormalizedResponse:
        query = self._traduz(recurso, params, PARAMS_PROPOSICOES)
        bruto = await self.get_json("/proposicoes", params=query)
        return self._envelopa(recurso, bruto, params, self._norm_proposicao)

    def _traduz(self, recurso: str, params: dict, mapa: dict[str, str]) -> dict:
        invalidos = sorted(set(params) - set(mapa))
        if invalidos:
            raise ParametroInvalido(recurso, invalidos, sorted(mapa))
        query = {mapa[k]: v for k, v in params.items()}
        if "siglaUf" in query:
            uf = normaliza_uf(query["siglaUf"])
            if uf is None:
                raise ParametroInvalido(recurso, ["uf"], sorted(mapa))
            query["siglaUf"] = uf
        return query

    def _envelopa(self, recurso, bruto, params, normalizador) -> NormalizedResponse:
        itens = []
        descartados = 0
        for item in bruto.get("dados", []):
            try:
                itens.append(normalizador(item).model_dump(mode="json"))
            except (ValidationError, KeyError, InvalidOperation):
                # registro podre nao derruba o lote, mas fica contado no meta
                descartados += 1
        links = bruto.get("links", [])
        meta = {
            "pagina": int(params["pagina"]) if str(params.get("pagina", "")).isdigit() else 1,
            "tem_proxima": any(l.get("rel") == "next" for l in links),
        }
        if descartados:
            meta["descartados"] = descartados
        return NormalizedResponse(
            fonte=self.name,
            recurso=recurso,
            dados=itens,
            total=len(itens),
            meta=meta,
        )

    def _norm_deputado(self, b: dict) -> Deputado:
        return Deputado(
            id=b["id"],
            nome=limpa_texto(b.get("nome")),
            partido=b.get("siglaPartido"),
            uf=normaliza_uf(b.get("siglaUf")),
            legislatura=b.get("idLegislatura"),
            email=b.get("email"),
            foto=b.get("urlFoto"),
        )

    def _norm_despesa(self, b: dict, dep_id: int) -> Despesa:
        return Despesa(
            deputado_id=dep_id,
            ano=b["ano"],
            mes=b["mes"],
            tipo=limpa_texto(b.get("tipoDespesa")),
            fornecedor=limpa_texto(b.get("nomeFornecedor")),
            fornecedor_doc=so_digitos(b.get("cnpjCpfFornecedor")),
            data=para_data(b.get("dataDocumento")),
            valor=Decimal(str(b.get("valorLiquido") or "0")),
            url_documento=b.get("urlDocumento") or None,
        )

    def _norm_votacao(self, b: dict) -> Votacao:
        # aprovacao vem como 0/1 e as vezes nem vem
        aprovacao = b.get("aprovacao")
        return Votacao(
            id=str(b["id"]),
            data=para_data(b.get("data") or b.get("dataHoraRegistro")),
            orgao=b.get("siglaOrgao"),
            descricao=limpa_texto(b.get("descricao")),
            aprovada=bool(aprovacao) if aprovacao is not None else None,
        )

    def _norm_voto(self, b: dict, vid: str) -> VotoDeputado:
        dep = b.get("deputado_") or {}
        return VotoDeputado(
            votacao_id=vid,
            voto=limpa_texto(b.get("tipoVoto")),
            deputado_id=dep["id"],
            deputado=limpa_texto(dep.get("nome")),
            partido=dep.get("siglaPartido"),
            uf=normaliza_uf(dep.get("siglaUf")),
            data=para_data(b.get("dataRegistroVoto")),
        )

    def _norm_proposicao(self, b: dict) -> Proposicao:
        return Proposicao(
            id=b["id"],
            tipo=b.get("siglaTipo") or "",
            numero=b.get("numero"),
            ano=b.get("ano") or None,
            ementa=limpa_texto(b.get("ementa")),
        )
