from typing import Any

from pydantic import ValidationError

from balcao.connectors.base import BaseConnector, NormalizedResponse, register
from balcao.exceptions import ParametroInvalido, RecursoNaoEncontrado
from balcao.models import Estado, Municipio
from balcao.normalize import normaliza_uf


@register
class IbgeConnector(BaseConnector):
    name = "ibge"
    base_url = "https://servicodados.ibge.gov.br/api/v1"
    description = "IBGE: estados e municípios do Brasil"
    suporta_busca = True
    resources = {
        "estados": "as 27 unidades da federação; sem filtros",
        "municipios": "municípios do país; filtros: uf (sem ele vêm os 5570)",
    }

    async def fetch(self, recurso: str, **params: Any) -> NormalizedResponse:
        partes = [p for p in recurso.strip("/").split("/") if p]
        match partes:
            case ["estados"]:
                return await self._estados(recurso, params)
            case ["municipios"]:
                return await self._municipios(recurso, params)
            case _:
                raise RecursoNaoEncontrado(self.name, recurso, sorted(self.resources))

    async def buscar(self, q: str) -> list[dict]:
        termo = q.casefold()
        estados = await self._estados("estados", {})
        achados = [
            {"tipo_resultado": "estado", **e}
            for e in estados.dados
            if termo in e["nome"].casefold() or termo == e["sigla"].casefold()
        ]
        municipios = await self._municipios("municipios", {})
        achados += [
            {"tipo_resultado": "municipio", **m}
            for m in municipios.dados
            if termo in m["nome"].casefold()
        ][:10]
        return achados

    async def _estados(self, recurso: str, params: dict) -> NormalizedResponse:
        if params:
            raise ParametroInvalido(recurso, sorted(params), [])
        bruto = await self.get_json("/localidades/estados", params={"orderBy": "nome"})
        itens, descartados = self._normaliza_lote(bruto, self._norm_estado)
        return self._envelopa(recurso, itens, descartados)

    async def _municipios(self, recurso: str, params: dict) -> NormalizedResponse:
        invalidos = sorted(set(params) - {"uf"})
        if invalidos:
            raise ParametroInvalido(recurso, invalidos, ["uf"])
        uf = normaliza_uf(params.get("uf"))
        if params.get("uf") and uf is None:
            raise ParametroInvalido(recurso, ["uf"], ["uf"])

        path = f"/localidades/estados/{uf}/municipios" if uf else "/localidades/municipios"
        bruto = await self.get_json(path, params={"orderBy": "nome"})
        itens, descartados = self._normaliza_lote(bruto, self._norm_municipio)
        return self._envelopa(recurso, itens, descartados)

    def _normaliza_lote(self, bruto: list, normalizador) -> tuple[list, int]:
        itens = []
        descartados = 0
        for b in bruto or []:
            try:
                itens.append(normalizador(b).model_dump(mode="json"))
            except (ValidationError, KeyError):
                descartados += 1
        return itens, descartados

    def _envelopa(self, recurso: str, itens: list, descartados: int) -> NormalizedResponse:
        meta = {"descartados": descartados} if descartados else {}
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=itens, total=len(itens), meta=meta
        )

    def _norm_estado(self, b: dict) -> Estado:
        return Estado(
            id=b["id"],
            sigla=b["sigla"],
            nome=b["nome"],
            regiao=(b.get("regiao") or {}).get("nome"),
        )

    def _norm_municipio(self, b: dict) -> Municipio:
        # a UF do municipio vem enterrada em tres niveis de aninhamento, e o
        # caminho muda conforme a divisao territorial usada na resposta
        uf_info = (((b.get("microrregiao") or {}).get("mesorregiao") or {}).get("UF") or {})
        if not uf_info:
            uf_info = (
                ((b.get("regiao-imediata") or {}).get("regiao-intermediaria") or {}).get("UF")
                or {}
            )
        return Municipio(
            id=b["id"],
            nome=b["nome"],
            uf=uf_info.get("sigla"),
            regiao=(uf_info.get("regiao") or {}).get("nome"),
        )
