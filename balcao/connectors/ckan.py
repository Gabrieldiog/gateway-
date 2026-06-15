from typing import Any

from pydantic import ValidationError

from balcao.connectors.base import BaseConnector, NormalizedResponse, register
from balcao.exceptions import ParametroInvalido, RecursoNaoEncontrado
from balcao.models import DatasetCKAN

# muitos portais de dados abertos do governo rodam CKAN, com a mesma API
# (/api/3/action/...). Esta classe é o motor: quem implementa CKAN só precisa
# de uma subclasse com name + base_url. Os dados de verdade saem do datastore.
FILTROS = {"q", "limite", "pagina"}
LIMITE_PADRAO = 10
LIMITE_MAX = 100
TIMEOUT = 30.0


class CKANConnector(BaseConnector):
    """Motor genérico de portais CKAN. Não é registrado — as fontes concretas
    (ANEEL, MME, ANTT...) são subclasses com name e base_url."""

    resources = {
        "datasets": f"conjuntos de dados (CKAN package_search); filtros: {', '.join(sorted(FILTROS))}",
        "dados/{recurso_id}": "linhas de um recurso com datastore (datastore_search); filtros: q, limite, pagina",
    }

    async def fetch(self, recurso: str, **params: Any) -> NormalizedResponse:
        partes = [p for p in recurso.strip("/").split("/") if p]
        match partes:
            case ["datasets"]:
                return await self._datasets(recurso, params)
            case ["dados", recurso_id]:
                return await self._dados(recurso, recurso_id, params)
            case _:
                raise RecursoNaoEncontrado(self.name, recurso, sorted(self.resources))

    async def _datasets(self, recurso: str, params: dict) -> NormalizedResponse:
        limite, offset, pagina = self._paginacao(recurso, params)
        consulta = {"q": params.get("q") or "*:*", "rows": limite, "start": offset}
        res = await self._action(recurso, "package_search", consulta)

        itens, descartados = [], 0
        for ds in res.get("results", []):
            try:
                itens.append(self._norm_dataset(ds).model_dump(mode="json"))
            except (ValidationError, KeyError):
                descartados += 1
        total = res.get("count")
        meta: dict[str, Any] = {
            "pagina": pagina,
            "total": total,
            "tem_proxima": total is not None and offset + limite < total,
        }
        if descartados:
            meta["descartados"] = descartados
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=itens, total=len(itens), meta=meta
        )

    async def _dados(self, recurso: str, recurso_id: str, params: dict) -> NormalizedResponse:
        limite, offset, pagina = self._paginacao(recurso, params)
        consulta: dict[str, Any] = {"resource_id": recurso_id, "limit": limite, "offset": offset}
        if params.get("q"):
            consulta["q"] = params["q"]
        res = await self._action(recurso, "datastore_search", consulta)

        registros = res.get("records", [])
        campos = [f.get("id") for f in res.get("fields", []) if f.get("id") != "_id"]
        total = res.get("total")
        meta = {
            "pagina": pagina,
            "total": total,
            "campos": campos,
            "tem_proxima": total is not None and offset + limite < total,
        }
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=registros, total=len(registros), meta=meta
        )

    async def _action(self, recurso: str, acao: str, params: dict) -> dict:
        bruto = await self.get_json(f"/api/3/action/{acao}", params=params, timeout=TIMEOUT)
        # o CKAN responde 200 com success=false em erro de lógica (id inexistente,
        # recurso sem datastore). Vira um 404 limpo nosso em vez de vazar o payload.
        if not isinstance(bruto, dict) or not bruto.get("success"):
            raise RecursoNaoEncontrado(self.name, recurso, sorted(self.resources))
        return bruto.get("result") or {}

    def _norm_dataset(self, ds: dict) -> DatasetCKAN:
        org = ds.get("organization") or {}
        recursos = [
            {
                "id": r.get("id"),
                "nome": r.get("name"),
                "formato": (r.get("format") or "").upper() or None,
                "datastore": bool(r.get("datastore_active")),
            }
            for r in ds.get("resources", [])
        ]
        return DatasetCKAN(
            fonte=self.name,
            id=ds.get("id") or ds.get("name") or "",
            nome=ds.get("name") or "",
            titulo=ds.get("title") or ds.get("name") or "",
            organizacao=org.get("title") or org.get("name"),
            atualizado=ds.get("metadata_modified"),
            recursos=recursos,
        )

    def _paginacao(self, recurso: str, params: dict) -> tuple[int, int, int]:
        invalidos = sorted(set(params) - FILTROS)
        if invalidos:
            raise ParametroInvalido(recurso, invalidos, sorted(FILTROS))
        limite = self._inteiro(recurso, "limite", params.get("limite"), LIMITE_PADRAO)
        limite = max(1, min(limite, LIMITE_MAX))
        pagina = max(1, self._inteiro(recurso, "pagina", params.get("pagina"), 1))
        return limite, (pagina - 1) * limite, pagina

    def _inteiro(self, recurso: str, nome: str, valor: Any, padrao: int) -> int:
        if valor is None:
            return padrao
        if not str(valor).isdigit():
            raise ParametroInvalido(recurso, [f"{nome}={valor}"], [f"{nome} numérico"])
        return int(valor)


@register
class AneelConnector(CKANConnector):
    name = "aneel"
    base_url = "https://dadosabertos.aneel.gov.br"
    description = "ANEEL (CKAN): tarifas, geração e empreendimentos do setor elétrico"


@register
class MmeConnector(CKANConnector):
    name = "mme"
    base_url = "https://dadosabertos.mme.gov.br"
    description = "Ministério de Minas e Energia (CKAN): energia, outorgas e mineração"


@register
class AnttConnector(CKANConnector):
    name = "antt"
    base_url = "https://dados.antt.gov.br"
    description = "ANTT (CKAN): transporte terrestre — fiscalização, fretes e concessões"
