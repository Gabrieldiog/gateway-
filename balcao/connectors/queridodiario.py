"""Querido Diário (Open Knowledge Brasil): busca por texto nos diários
oficiais de centenas de prefeituras. É a fonte hiperlocal por excelência —
"dispensa de licitação", o nome de uma empresa, "nomeação" — direto do
papel oficial da cidade. Sem chave; a cobertura não é universal, então
municipio sem diário é caso normal, não erro."""

from typing import Any

from balcao.connectors.base import BaseConnector, NormalizedResponse, register
from balcao.exceptions import ParametroInvalido, RecursoNaoEncontrado
from balcao.models import CidadeDiario, DiarioOficial
from balcao.normalize import limpa_texto, para_data, so_digitos

FONTE = {
    "nome": "Querido Diário — Open Knowledge Brasil",
    "url": "https://queridodiario.ok.org.br",
    "nota": (
        "Projeto da sociedade civil que liberta os diários oficiais municipais: "
        "coleta, extrai o texto e abre a busca. A cobertura cresce cidade a "
        "cidade — nem todo município está no radar ainda."
    ),
}


@register
class QueridoDiarioConnector(BaseConnector):
    name = "diarios"
    base_url = "https://api.queridodiario.ok.org.br"
    description = "Querido Diário: busca nos diários oficiais municipais (OKBR)"
    resources = {
        "busca": "trechos de diários oficiais (params: municipio = código IBGE, q = termo, de/ate = AAAA-MM-DD, pagina)",
        "cobertura": "municípios cobertos (param: nome = começo do nome da cidade)",
    }

    async def fetch(self, recurso: str, **params: Any) -> NormalizedResponse:
        partes = [p for p in recurso.strip("/").split("/") if p]
        match partes:
            case ["busca"]:
                return await self._busca(recurso, params)
            case ["cobertura"]:
                return await self._cobertura(recurso, params)
            case _:
                raise RecursoNaoEncontrado(self.name, recurso, sorted(self.resources))

    def _valida(self, recurso: str, params: dict, aceitos: set) -> None:
        invalidos = sorted(set(params) - aceitos)
        if invalidos:
            raise ParametroInvalido(recurso, invalidos, sorted(aceitos))

    async def _busca(self, recurso: str, params: dict) -> NormalizedResponse:
        self._valida(recurso, params, {"municipio", "q", "de", "ate", "pagina"})
        ibge = so_digitos(str(params.get("municipio", ""))) or ""
        if len(ibge) != 7:
            raise ParametroInvalido(recurso, ["municipio"], ["municipio = código IBGE de 7 dígitos"])
        q = str(params.get("q", "")).strip()
        if not q:
            raise ParametroInvalido(recurso, ["q"], ["q = termo de busca (aspas buscam a frase exata)"])
        pagina = str(params.get("pagina", 1))
        if not pagina.isdigit() or int(pagina) < 1:
            raise ParametroInvalido(recurso, ["pagina"], ["pagina >= 1"])
        tamanho = 10
        consulta: dict = {
            "territory_ids": ibge,
            "querystring": q,
            "size": tamanho,
            "offset": (int(pagina) - 1) * tamanho,
            "excerpt_size": 400,
            "number_of_excerpts": 2,
            "sort_by": "descending_date",
        }
        if params.get("de"):
            consulta["published_since"] = str(params["de"])
        if params.get("ate"):
            consulta["published_until"] = str(params["ate"])
        bruto = await self.get_json("/gazettes", params=consulta, timeout=30)

        itens = []
        for g in bruto.get("gazettes", []) if isinstance(bruto, dict) else []:
            url = g.get("url")
            if not url:
                continue
            itens.append(
                DiarioOficial(
                    municipio=limpa_texto(g.get("territory_name")) or ibge,
                    uf=g.get("state_code"),
                    data=para_data(g.get("date")),
                    edicao=str(g.get("edition") or "") or None,
                    extra=bool(g.get("is_extra_edition")),
                    trechos=[t for t in (g.get("excerpts") or []) if t],
                    url=url,
                    url_texto=g.get("txt_url") or None,
                ).model_dump(mode="json")
            )
        total = int(bruto.get("total_gazettes") or 0) if isinstance(bruto, dict) else 0
        meta = {
            "q": q,
            "municipio": ibge,
            "total_diarios": total,
            "pagina": int(pagina),
            "tem_proxima": int(pagina) * tamanho < total,
            "fonte": FONTE,
        }
        if not itens:
            meta["aviso"] = (
                "nada encontrado — pode ser falta de cobertura da cidade ou o termo não aparece"
            )
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=itens, total=len(itens), meta=meta
        )

    async def _cobertura(self, recurso: str, params: dict) -> NormalizedResponse:
        self._valida(recurso, params, {"nome"})
        nome = str(params.get("nome", "")).strip()
        if len(nome) < 3:
            raise ParametroInvalido(recurso, ["nome"], ["nome = pelo menos 3 letras da cidade"])
        bruto = await self.get_json("/cities", params={"city_name": nome}, timeout=20)
        itens = []
        for c in bruto.get("cities", []) if isinstance(bruto, dict) else []:
            try:
                itens.append(
                    CidadeDiario(
                        ibge=int(c["territory_id"]),
                        nome=limpa_texto(c.get("territory_name")) or "",
                        uf=c.get("state_code"),
                    ).model_dump(mode="json")
                )
            except (KeyError, ValueError, TypeError):
                continue
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=itens, total=len(itens),
            meta={"nome": nome, "fonte": FONTE},
        )
