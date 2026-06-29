from typing import Any

from pydantic import ValidationError

from balcao.connectors.base import BaseConnector, NormalizedResponse, register
from balcao.exceptions import ParametroInvalido, RecursoNaoEncontrado
from balcao.models import Senador, VotoSenador
from balcao.normalize import limpa_texto, normaliza_uf, para_data

PARAMS_SENADORES = {"uf", "partido"}

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
    description = "Senado Federal: senadores em exercício"
    suporta_busca = True
    resources = {
        "senadores": f"senadores em exercício; filtros: {', '.join(sorted(PARAMS_SENADORES))}",
        "senadores/{id}": "detalhe de um senador",
        "senadores/{id}/votos": "histórico de votos de um senador (matéria, voto, resultado)",
    }

    async def fetch(self, recurso: str, **params: Any) -> NormalizedResponse:
        partes = [p for p in recurso.strip("/").split("/") if p]
        match partes:
            case ["senadores"]:
                return await self._senadores(recurso, params)
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
