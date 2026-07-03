"""BrasilAPI: a ficha cadastral de um CNPJ na Receita Federal, sem chave.
É o conector utilitário que dá nome, situação e sócios a qualquer CNPJ que
aparecer nas outras fontes — a cola da Ficha do Fornecedor."""

from typing import Any

from balcao.connectors.base import BaseConnector, NormalizedResponse, register
from balcao.exceptions import ParametroInvalido, RecursoNaoEncontrado
from balcao.models import FichaEmpresa
from balcao.normalize import limpa_texto, para_data, so_digitos, valor_br

FONTE = {
    "nome": "BrasilAPI — dados da Receita Federal",
    "url": "https://brasilapi.com.br",
    "nota": (
        "Ficha cadastral pública do CNPJ (razão social, situação, sócios), "
        "espelhada da Receita Federal pela BrasilAPI, projeto aberto da "
        "comunidade brasileira."
    ),
}


@register
class BrasilApiConnector(BaseConnector):
    name = "brasilapi"
    base_url = "https://brasilapi.com.br/api"
    description = "BrasilAPI: ficha cadastral de CNPJ (razão social, situação, CNAE, sócios)"
    resources = {
        "cnpj/{cnpj}": "ficha da empresa na Receita (aceita CNPJ com ou sem máscara)",
    }

    async def fetch(self, recurso: str, **params: Any) -> NormalizedResponse:
        partes = [p for p in recurso.strip("/").split("/") if p]
        match partes:
            # CNPJ com máscara tem barra (04.984.400/0001-30): junta os pedaços
            case ["cnpj", *doc_partes] if doc_partes:
                return await self._cnpj(recurso, "".join(doc_partes))
            case _:
                raise RecursoNaoEncontrado(self.name, recurso, sorted(self.resources))

    async def _cnpj(self, recurso: str, doc: str) -> NormalizedResponse:
        cnpj = so_digitos(doc) or ""
        if len(cnpj) != 14:
            raise ParametroInvalido(recurso, ["cnpj"], ["cnpj de 14 dígitos"])
        b = await self.get_json(f"/cnpj/v1/{cnpj}")

        ficha = FichaEmpresa(
            cnpj=cnpj,
            razao_social=limpa_texto(b.get("razao_social")) or "—",
            nome_fantasia=limpa_texto(b.get("nome_fantasia")) or None,
            situacao=limpa_texto(b.get("descricao_situacao_cadastral")) or None,
            natureza=limpa_texto(b.get("natureza_juridica")) or None,
            abertura=para_data(b.get("data_inicio_atividade")),
            atividade=limpa_texto(b.get("cnae_fiscal_descricao")) or None,
            capital_social=valor_br(b.get("capital_social")),
            municipio=limpa_texto(b.get("municipio")) or None,
            uf=b.get("uf") or None,
            socios=[
                s["nome_socio"]
                for s in (b.get("qsa") or [])
                if isinstance(s, dict) and s.get("nome_socio")
            ],
        )
        return NormalizedResponse(
            fonte=self.name,
            recurso=recurso,
            dados=[ficha.model_dump(mode="json")],
            total=1,
            meta={"fonte": FONTE},
        )
