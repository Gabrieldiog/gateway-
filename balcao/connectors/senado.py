from datetime import date
from typing import Any

from pydantic import ValidationError

from balcao.connectors.base import BaseConnector, NormalizedResponse, register
from balcao.exceptions import ParametroInvalido, RecursoNaoEncontrado
from balcao.models import Materia, Senador, VotoSenador
from balcao.normalize import limpa_texto, normaliza_uf, para_data

PARAMS_SENADORES = {"uf", "partido"}
PARAMS_MATERIAS = {"tipo", "ano", "tramitando", "limit"}

# o Senado abrevia o voto; aqui viram rótulos legíveis (e absenteísmos explícitos)
MAP_VOTO_SENADO = {
    "Sim": "Sim",
    "Não": "Não",
    "Abstenção": "Abstenção",
    "Votou": "Votou",  # votação secreta: registrou voto, mas a escolha não é pública
    "P-NRV": "Presidente",  # presidindo a sessão, não vota
    "MIS": "Missão",
    "AP": "Ausente",
    "NCom": "Ausente",
    "LA": "Licença",
    "LS": "Licença",
    "LP": "Licença",
}


@register
class SenadoConnector(BaseConnector):
    name = "senado"
    base_url = "https://legis.senado.leg.br/dadosabertos"
    description = "Senado Federal: senadores em exercício e matérias em tramitação"
    suporta_busca = True
    resources = {
        "senadores": f"senadores em exercício; filtros: {', '.join(sorted(PARAMS_SENADORES))}",
        "senadores/{id}": "detalhe de um senador",
        "senadores/{id}/votos": "histórico de votos de um senador (matéria, voto, resultado)",
        "materias": f"matérias legislativas (API nova de processos); filtros: {', '.join(sorted(PARAMS_MATERIAS))}",
    }

    async def fetch(self, recurso: str, **params: Any) -> NormalizedResponse:
        partes = [p for p in recurso.strip("/").split("/") if p]
        match partes:
            case ["senadores"]:
                return await self._senadores(recurso, params)
            case ["materias"]:
                return await self._materias(recurso, params)
            case ["senadores", sen_id, "votos"] if sen_id.isdigit():
                return await self._votos_senador(recurso, int(sen_id))
            case ["senadores", sen_id] if sen_id.isdigit():
                return await self._senador_detalhe(recurso, int(sen_id))
            case _:
                raise RecursoNaoEncontrado(self.name, recurso, sorted(self.resources))

    async def buscar(self, q: str) -> list[dict]:
        resposta = await self._senadores("senadores", {})
        termo = q.casefold()
        return [
            {"tipo_resultado": "senador", **s}
            for s in resposta.dados
            if termo in s["nome"].casefold()
        ]

    async def _senadores(self, recurso: str, params: dict) -> NormalizedResponse:
        invalidos = sorted(set(params) - PARAMS_SENADORES)
        if invalidos:
            raise ParametroInvalido(recurso, invalidos, sorted(PARAMS_SENADORES))
        uf = normaliza_uf(params.get("uf"))
        if params.get("uf") and uf is None:
            raise ParametroInvalido(recurso, ["uf"], sorted(PARAMS_SENADORES))
        partido = str(params.get("partido", "")).strip().upper() or None

        bruto = await self.get_json("/senador/lista/atual")
        # a fonte enterra a lista em tres niveis de envelope
        lista = (
            (bruto.get("ListaParlamentarEmExercicio") or {})
            .get("Parlamentares", {})
            .get("Parlamentar", [])
        )

        itens = []
        descartados = 0
        for b in lista:
            try:
                senador = self._norm_senador(b.get("IdentificacaoParlamentar", {}))
            except (ValidationError, KeyError, TypeError):
                descartados += 1
                continue
            # o Senado nao filtra a lista atual, entao o recorte e nosso
            if uf and senador.uf != uf:
                continue
            if partido and senador.partido != partido:
                continue
            itens.append(senador.model_dump(mode="json"))

        meta = {"descartados": descartados} if descartados else {}
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=itens, total=len(itens), meta=meta
        )

    async def _materias(self, recurso: str, params: dict) -> NormalizedResponse:
        # a API antiga de matérias foi desativada em fev/2026; esta é a
        # substituta oficial (/processo), que fala JSON de verdade
        invalidos = sorted(set(params) - PARAMS_MATERIAS)
        if invalidos:
            raise ParametroInvalido(recurso, invalidos, sorted(PARAMS_MATERIAS))
        tipo = str(params.get("tipo", "PL")).strip().upper()
        ano = str(params.get("ano", date.today().year))
        if not ano.isdigit():
            raise ParametroInvalido(recurso, ["ano"], sorted(PARAMS_MATERIAS))
        tramitando = str(params.get("tramitando", "")).strip().lower()
        if tramitando not in ("", "sim", "nao", "não"):
            raise ParametroInvalido(recurso, ["tramitando"], ["sim", "nao"])
        limit = params.get("limit", 50)
        if not str(limit).isdigit() or not (1 <= int(limit) <= 200):
            raise ParametroInvalido(recurso, ["limit"], ["1..200"])

        bruto = await self.get_json("/processo", params={"sigla": tipo, "ano": int(ano)})

        itens, descartados = [], 0
        for p in bruto if isinstance(bruto, list) else []:
            try:
                materia = self._norm_materia(p)
            except (ValidationError, KeyError, TypeError):
                descartados += 1
                continue
            if tramitando and materia.tramitando != (tramitando == "sim"):
                continue
            itens.append(materia.model_dump(mode="json"))
        # o que se mexeu mais recentemente vem primeiro
        itens.sort(key=lambda m: m.get("atualizada_em") or "", reverse=True)
        itens = itens[: int(limit)]

        meta: dict = {"tipo": tipo, "ano": int(ano)}
        if descartados:
            meta["descartados"] = descartados
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=itens, total=len(itens), meta=meta
        )

    @staticmethod
    def _norm_materia(p: dict) -> Materia:
        situacao = p.get("situacaoAtual")
        if isinstance(situacao, dict):
            situacao = situacao.get("descricao") or situacao.get("nome")
        return Materia(
            id=int(p["id"]),
            identificacao=limpa_texto(p.get("identificacao")),
            ementa=limpa_texto(p.get("ementa")),
            autor=limpa_texto(p.get("autoria")) or None,
            apresentada_em=para_data(p.get("dataApresentacao")),
            situacao=limpa_texto(str(situacao)) or None if situacao else None,
            situacao_em=para_data(p.get("dataSituacaoAtual")),
            atualizada_em=para_data(p.get("dataUltimaAtualizacao")),
            tramitando=str(p.get("tramitando", "")).strip().lower() == "sim",
            url=p.get("urlDocumento") or None,
        )

    async def _senador_detalhe(self, recurso: str, sen_id: int) -> NormalizedResponse:
        bruto = await self.get_json(f"/senador/{sen_id}")
        ident = (
            (bruto.get("DetalheParlamentar") or {})
            .get("Parlamentar", {})
            .get("IdentificacaoParlamentar", {})
        )
        senador = self._norm_senador(ident)
        return NormalizedResponse(
            fonte=self.name,
            recurso=recurso,
            dados=[senador.model_dump(mode="json")],
            total=1,
        )

    async def _votos_senador(self, recurso: str, codigo: int) -> NormalizedResponse:
        # a API nova devolve o histórico inteiro do senador numa lista crua
        bruto = await self.get_json("/votacao", params={"codigoParlamentar": codigo})
        itens, descartados = [], 0
        for it in bruto if isinstance(bruto, list) else []:
            try:
                itens.append(self._norm_voto_senador(it).model_dump(mode="json"))
            except (ValidationError, KeyError, TypeError):
                descartados += 1
        itens.sort(key=lambda v: v.get("data") or "", reverse=True)  # recentes primeiro
        meta = {"descartados": descartados} if descartados else {}
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=itens, total=len(itens), meta=meta
        )

    def _norm_voto_senador(self, it: dict) -> VotoSenador:
        voto_bruto = (it.get("votos") or [{}])[0]
        sigla = (voto_bruto.get("siglaVotoParlamentar") or "").strip()
        resultado = it.get("resultadoVotacao")
        return VotoSenador(
            votacao_id=str(it.get("codigoSessaoVotacao") or it.get("codigoVotacaoSve") or ""),
            data=para_data(it.get("dataSessao")),
            voto=MAP_VOTO_SENADO.get(sigla, sigla or "—"),
            descricao=limpa_texto(it.get("ementa") or it.get("descricaoVotacao")),
            materia=it.get("identificacao") or None,
            aprovada=(resultado == "A") if resultado in ("A", "R") else None,
            secreta=it.get("votacaoSecreta") == "S",
        )

    def _norm_senador(self, ident: dict) -> Senador:
        return Senador(
            id=int(ident["CodigoParlamentar"]),
            nome=limpa_texto(ident.get("NomeParlamentar")),
            partido=(ident.get("SiglaPartidoParlamentar") or "").strip().upper() or None,
            uf=normaliza_uf(ident.get("UfParlamentar")),
            email=ident.get("EmailParlamentar") or None,
            foto=ident.get("UrlFotoParlamentar") or None,
        )
