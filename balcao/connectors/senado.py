from typing import Any

from pydantic import ValidationError

from balcao.connectors.base import BaseConnector, NormalizedResponse, register
from balcao.exceptions import ParametroInvalido, RecursoNaoEncontrado
from balcao.models import Senador
from balcao.normalize import limpa_texto, normaliza_uf

PARAMS_SENADORES = {"uf", "partido"}


@register
class SenadoConnector(BaseConnector):
    name = "senado"
    base_url = "https://legis.senado.leg.br/dadosabertos"
    description = "Senado Federal: senadores em exercício"
    resources = {
        "senadores": f"senadores em exercício; filtros: {', '.join(sorted(PARAMS_SENADORES))}",
        "senadores/{id}": "detalhe de um senador",
    }

    async def fetch(self, recurso: str, **params: Any) -> NormalizedResponse:
        partes = [p for p in recurso.strip("/").split("/") if p]
        match partes:
            case ["senadores"]:
                return await self._senadores(recurso, params)
            case ["senadores", sen_id] if sen_id.isdigit():
                return await self._senador_detalhe(recurso, int(sen_id))
            case _:
                raise RecursoNaoEncontrado(self.name, recurso, sorted(self.resources))

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

    def _norm_senador(self, ident: dict) -> Senador:
        return Senador(
            id=int(ident["CodigoParlamentar"]),
            nome=limpa_texto(ident.get("NomeParlamentar")),
            partido=(ident.get("SiglaPartidoParlamentar") or "").strip().upper() or None,
            uf=normaliza_uf(ident.get("UfParlamentar")),
            email=ident.get("EmailParlamentar") or None,
            foto=ident.get("UrlFotoParlamentar") or None,
        )
