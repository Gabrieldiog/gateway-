from typing import Any

from pydantic import ValidationError

from balcao.connectors.base import BaseConnector, NormalizedResponse, register
from balcao.exceptions import ParametroInvalido, RecursoNaoEncontrado
from balcao.models import PontoIpea, SerieIpea
from balcao.normalize import para_data

LIMITE_PADRAO = 20
LIMITE_MAX = 100
ULTIMOS_PADRAO = 30


@register
class IpeadataConnector(BaseConnector):
    name = "ipeadata"
    base_url = "http://www.ipeadata.gov.br/api/odata4"
    description = "IPEADATA: séries macroeconômicas, regionais e sociais (PIB, inflação, emprego...)"
    suporta_busca = True
    resources = {
        "series": "catálogo de séries (busca por nome); filtros: q, limite, pagina",
        "serie/{codigo}": "valores de uma série; filtros: ultimos",
    }

    async def fetch(self, recurso: str, **params: Any) -> NormalizedResponse:
        partes = [p for p in recurso.strip("/").split("/") if p]
        match partes:
            case ["series"]:
                return await self._series(recurso, params)
            case ["serie", codigo]:
                return await self._valores(recurso, codigo, params)
            case _:
                raise RecursoNaoEncontrado(self.name, recurso, sorted(self.resources))

    async def buscar(self, q: str) -> list[dict]:
        resposta = await self._series("series", {"q": q, "limite": 10})
        return [{"tipo_resultado": "serie", **s} for s in resposta.dados]

    async def _series(self, recurso: str, params: dict) -> NormalizedResponse:
        invalidos = sorted(set(params) - {"q", "limite", "pagina"})
        if invalidos:
            raise ParametroInvalido(recurso, invalidos, ["q", "limite", "pagina"])
        limite = self._inteiro(recurso, "limite", params.get("limite"), LIMITE_PADRAO)
        limite = max(1, min(limite, LIMITE_MAX))
        pagina = max(1, self._inteiro(recurso, "pagina", params.get("pagina"), 1))

        # o OData do IPEADATA não tem contains; startswith no nome é o que ele aceita
        consulta: dict[str, Any] = {"$top": limite, "$skip": (pagina - 1) * limite}
        if params.get("q"):
            termo = str(params["q"]).replace("'", "''")
            consulta["$filter"] = f"startswith(SERNOME,'{termo}')"

        bruto = await self.get_json("/Metadados", params=consulta)
        registros = bruto.get("value", []) if isinstance(bruto, dict) else []
        itens, descartados = [], 0
        for s in registros:
            try:
                itens.append(self._norm_serie(s).model_dump(mode="json"))
            except (ValidationError, KeyError):
                descartados += 1
        meta: dict[str, Any] = {"pagina": pagina, "tem_proxima": len(registros) >= limite}
        if descartados:
            meta["descartados"] = descartados
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=itens, total=len(itens), meta=meta
        )

    async def _valores(self, recurso: str, codigo: str, params: dict) -> NormalizedResponse:
        invalidos = sorted(set(params) - {"ultimos"})
        if invalidos:
            raise ParametroInvalido(recurso, invalidos, ["ultimos"])
        ultimos = self._inteiro(recurso, "ultimos", params.get("ultimos"), ULTIMOS_PADRAO)

        # o ValoresSerie ignora $top/$orderby e devolve a série inteira (ascendente);
        # o recorte dos mais recentes é feito aqui
        seguro = codigo.replace("'", "''")
        bruto = await self.get_json(f"/ValoresSerie(SERCODIGO='{seguro}')")
        registros = bruto.get("value", []) if isinstance(bruto, dict) else []

        pontos, descartados = [], 0
        for v in registros:
            try:
                pontos.append(self._norm_ponto(v, codigo))
            except (ValidationError, KeyError):
                descartados += 1
        pontos.sort(key=lambda p: (p.data is None, p.data))  # ascendente, nulos no fim
        recorte = pontos[-ultimos:] if ultimos > 0 else pontos
        dados = [p.model_dump(mode="json") for p in recorte]

        meta: dict[str, Any] = {"total_serie": len(pontos)}
        if descartados:
            meta["descartados"] = descartados
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=dados, total=len(dados), meta=meta
        )

    def _norm_serie(self, s: dict) -> SerieIpea:
        return SerieIpea(
            codigo=s["SERCODIGO"],
            nome=s.get("SERNOME") or "",
            unidade=s.get("UNINOME") or None,
            periodicidade=s.get("PERNOME") or None,
            fonte_dados=s.get("FNTNOME") or None,
            base=s.get("BASNOME") or None,
            ativa=(s.get("SERSTATUS") or "A") == "A",
        )

    def _norm_ponto(self, v: dict, codigo: str) -> PontoIpea:
        bruto = v.get("VALVALOR")
        try:
            valor = float(bruto) if bruto is not None else None
        except (ValueError, TypeError):
            valor = None
        return PontoIpea(
            codigo=codigo,
            data=para_data(v.get("VALDATA")),
            valor=valor,
            territorio=(v.get("TERCODIGO") or v.get("NIVNOME") or "") or None,
        )

    def _inteiro(self, recurso: str, nome: str, valor: Any, padrao: int) -> int:
        if valor is None:
            return padrao
        texto = str(valor)
        if not texto.lstrip("-").isdigit():
            raise ParametroInvalido(recurso, [f"{nome}={valor}"], [f"{nome} numérico"])
        return int(texto)
