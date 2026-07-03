import asyncio
from decimal import Decimal, InvalidOperation
from typing import Any

from pydantic import ValidationError

from balcao.connectors.base import BaseConnector, NormalizedResponse, register
from balcao.exceptions import ParametroInvalido, RecursoNaoEncontrado
from balcao.models import (
    Deputado,
    Despesa,
    Discurso,
    OrientacaoBancada,
    PerfilDeputado,
    Proposicao,
    ProposicaoDetalhe,
    ProposicaoResumo,
    Votacao,
    VotacaoCompleta,
    VotoDeputado,
)
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
        "deputados/{id}/perfil": "perfil completo: formação, naturalidade, gabinete, redes sociais",
        "deputados/{id}/despesas": f"despesas CEAP com a nota fiscal; filtros: {', '.join(PARAMS_DESPESAS)}",
        "deputados/{id}/discursos": "discursos com sumário e transcrição (params: de, ate = AAAA-MM-DD, itens)",
        "votacoes": f"votações; filtros: {', '.join(PARAMS_VOTACOES)}",
        "votacoes/{id}": "a história da votação: parecer votado e proposições afetadas com ementa",
        "proposicoes/{id}": "dossiê de um projeto: situação, onde está, regime e o texto integral",
        "votacoes/{id}/votos": "voto de cada deputado (Sim/Não/Abstenção); só votação nominal tem",
        "votacoes/{id}/orientacoes": "como cada partido/bloco (e Governo/Oposição) orientou; só nas nominais",
        "proposicoes": f"proposições; filtros: {', '.join(PARAMS_PROPOSICOES)}",
    }

    async def fetch(self, recurso: str, **params: Any) -> NormalizedResponse:
        partes = [p for p in recurso.strip("/").split("/") if p]
        match partes:
            case ["deputados"]:
                return await self._deputados(recurso, params)
            case ["deputados", dep_id] if dep_id.isdigit():
                return await self._deputado_detalhe(recurso, int(dep_id))
            case ["deputados", dep_id, "perfil"] if dep_id.isdigit():
                return await self._perfil(recurso, int(dep_id))
            case ["deputados", dep_id, "despesas"] if dep_id.isdigit():
                return await self._despesas(recurso, int(dep_id), params)
            case ["deputados", dep_id, "discursos"] if dep_id.isdigit():
                return await self._discursos(recurso, int(dep_id), params)
            case ["votacoes"]:
                return await self._votacoes(recurso, params)
            case ["votacoes", vid, "votos"]:  # id tem hífen ("2629954-8"), não é só dígito
                return await self._votos(recurso, vid)
            case ["votacoes", vid, "orientacoes"]:
                return await self._orientacoes(recurso, vid)
            case ["votacoes", vid]:
                return await self._votacao_detalhe(recurso, vid)
            case ["proposicoes"]:
                return await self._proposicoes(recurso, params)
            case ["proposicoes", pid] if pid.isdigit():
                return await self._proposicao_detalhe(recurso, int(pid))
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

    async def _perfil(self, recurso: str, dep_id: int) -> NormalizedResponse:
        bruto = await self.get_json(f"/deputados/{dep_id}")
        d = bruto.get("dados", {})
        status = d.get("ultimoStatus", {})
        gabinete = status.get("gabinete") or {}
        cidade = limpa_texto(d.get("municipioNascimento"))
        uf_nasc = d.get("ufNascimento")
        sala = " · ".join(
            p for p in (
                f"prédio {gabinete['predio']}" if gabinete.get("predio") else None,
                f"sala {gabinete['sala']}" if gabinete.get("sala") else None,
            ) if p
        )
        perfil = PerfilDeputado(
            id=d["id"],
            nome=limpa_texto(status.get("nomeEleitoral") or status.get("nome") or d.get("nomeCivil")),
            nome_civil=limpa_texto(d.get("nomeCivil")) or None,
            partido=status.get("siglaPartido"),
            uf=normaliza_uf(status.get("siglaUf")),
            situacao=status.get("situacao"),
            condicao=status.get("condicaoEleitoral"),
            nascimento=para_data(d.get("dataNascimento")),
            naturalidade=" · ".join(p for p in (cidade, uf_nasc) if p) or None,
            escolaridade=limpa_texto(d.get("escolaridade")) or None,
            email=status.get("email") or gabinete.get("email"),
            telefone_gabinete=gabinete.get("telefone"),
            gabinete=sala or None,
            site=d.get("urlWebsite"),
            redes=[r for r in (d.get("redeSocial") or []) if r],
            foto=status.get("urlFoto"),
        )
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=[perfil.model_dump(mode="json")], total=1
        )

    async def _discursos(self, recurso: str, dep_id: int, params: dict) -> NormalizedResponse:
        mapa = {"de": "dataInicio", "ate": "dataFim", "itens": "itens", "pagina": "pagina"}
        query = self._traduz(recurso, params, mapa)
        query.setdefault("ordenarPor", "dataHoraInicio")
        query.setdefault("ordem", "DESC")
        bruto = await self.get_json(f"/deputados/{dep_id}/discursos", params=query)
        return self._envelopa(
            recurso, bruto, params, lambda b: self._norm_discurso(b, dep_id)
        )

    async def _orientacoes(self, recurso: str, vid: str) -> NormalizedResponse:
        bruto = await self.get_json(f"/votacoes/{vid}/orientacoes")
        itens = []
        for o in bruto.get("dados", []):
            bancada = limpa_texto(o.get("siglaPartidoBloco"))
            orientacao = limpa_texto(o.get("orientacaoVoto"))
            if not bancada or not orientacao:
                continue
            itens.append(
                OrientacaoBancada(
                    votacao_id=vid,
                    bancada=bancada,
                    orientacao=orientacao,
                    lideranca=o.get("codTipoLideranca"),
                ).model_dump(mode="json")
            )
        meta: dict[str, Any] = {}
        if not itens:
            meta["aviso"] = "votação simbólica não tem orientação registrada; só as nominais"
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=itens, total=len(itens), meta=meta
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
        dado = bruto.get("dados", {}) or {}
        base = self._norm_votacao(dado)
        parecer = limpa_texto(
            (dado.get("ultimaApresentacaoProposicao") or {}).get("descricao")
        )
        proposicoes = []
        # afetadas contam a historia; sem elas, os objetos com ementa quebram o galho
        candidatas = dado.get("proposicoesAfetadas") or [
            p for p in (dado.get("objetosPossiveis") or []) if p.get("ementa")
        ]
        for p in candidatas[:5]:
            ano = p.get("ano") or ""
            titulo = f"{p.get('siglaTipo') or ''} {p.get('numero') or ''}".strip()
            if ano and int(ano or 0) > 0:
                titulo = f"{titulo}/{ano}"
            try:
                proposicoes.append(
                    ProposicaoResumo(
                        id=p["id"], titulo=titulo, ementa=limpa_texto(p.get("ementa")) or None
                    )
                )
            except (ValidationError, KeyError):
                continue
        completa = VotacaoCompleta(
            **base.model_dump(),
            parecer=parecer or None,
            proposicoes=proposicoes,
        )
        return NormalizedResponse(
            fonte=self.name,
            recurso=recurso,
            dados=[completa.model_dump(mode="json")],
            total=1,
        )

    async def _proposicao_detalhe(self, recurso: str, pid: int) -> NormalizedResponse:
        bruto = await self.get_json(f"/proposicoes/{pid}")
        d = bruto.get("dados", {}) or {}
        status = d.get("statusProposicao") or {}
        detalhe = ProposicaoDetalhe(
            id=d["id"],
            tipo=d.get("siglaTipo") or "",
            numero=d.get("numero"),
            ano=d.get("ano") or None,
            ementa=limpa_texto(d.get("ementa")),
            ementa_detalhada=limpa_texto(d.get("ementaDetalhada")) or None,
            situacao=limpa_texto(status.get("descricaoSituacao")) or None,
            tramitacao=limpa_texto(status.get("descricaoTramitacao")) or None,
            orgao=status.get("siglaOrgao") or None,
            regime=limpa_texto(status.get("regime")) or None,
            despacho=limpa_texto(status.get("despacho")) or None,
            url_inteiro_teor=d.get("urlInteiroTeor") or None,
            keywords=limpa_texto(d.get("keywords")) or None,
        )
        return NormalizedResponse(
            fonte=self.name,
            recurso=recurso,
            dados=[detalhe.model_dump(mode="json")],
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
        def dec(campo: str) -> Decimal | None:
            v = b.get(campo)
            return Decimal(str(v)) if v not in (None, "") else None

        return Despesa(
            deputado_id=dep_id,
            ano=b["ano"],
            mes=b["mes"],
            tipo=limpa_texto(b.get("tipoDespesa")),
            fornecedor=limpa_texto(b.get("nomeFornecedor")),
            fornecedor_doc=so_digitos(b.get("cnpjCpfFornecedor")),
            data=para_data(b.get("dataDocumento")),
            valor=Decimal(str(b.get("valorLiquido") or "0")),
            valor_documento=dec("valorDocumento"),
            valor_glosa=dec("valorGlosa"),
            url_documento=b.get("urlDocumento") or None,
        )

    def _norm_discurso(self, b: dict, dep_id: int) -> Discurso:
        fase = b.get("faseEvento") or {}
        return Discurso(
            deputado_id=dep_id,
            data=b.get("dataHoraInicio"),
            tipo=limpa_texto(b.get("tipoDiscurso")) or None,
            sumario=limpa_texto(b.get("sumario")) or None,
            transcricao=limpa_texto(b.get("transcricao")) or None,
            evento=limpa_texto(fase.get("titulo")) or None,
            url_video=b.get("urlVideo") or None,
            url_audio=b.get("urlAudio") or None,
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
