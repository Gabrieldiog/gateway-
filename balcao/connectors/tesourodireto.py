"""Tesouro Direto (Tesouro Transparente): preço e taxa dos títulos públicos.
Não há API — é um CSV de ~14 MB com o histórico desde 2002, SEM ordem
cronológica (o topo é 2015, o fim é 2005), separado por ponto e vírgula e
com vírgula decimal. O conector baixa, varre tudo atrás da data-base mais
recente e devolve só a foto de hoje, normalizada. O cache do gateway evita
rebaixar o arquivo a cada request."""

from datetime import date
from typing import Any

from balcao.connectors.base import BaseConnector, NormalizedResponse, register
from balcao.exceptions import ErroUpstream, ParametroInvalido, RecursoNaoEncontrado
from balcao.models import TituloPublico
from balcao.normalize import para_data, valor_br

ARQUIVO = (
    "/dataset/df56aa42-484a-4a59-8184-7676580c81e3"
    "/resource/796d2059-14e9-44e3-80c9-2d9e30b405c1/download/precotaxatesourodireto.csv"
)

FONTE = {
    "nome": "Tesouro Direto — Tesouro Transparente",
    "url": "https://www.tesourotransparente.gov.br/ckan/dataset/taxas-dos-titulos-ofertados-pelo-tesouro-direto",
    "nota": (
        "Preços e taxas da manhã, publicados diariamente pelo Tesouro Nacional. "
        "PU é o preço unitário do título; a taxa é ao ano. Não é oferta de "
        "investimento — confira no site do Tesouro Direto antes de operar."
    ),
}


@register
class TesouroDiretoConnector(BaseConnector):
    name = "tesourodireto"
    base_url = "https://www.tesourotransparente.gov.br/ckan"
    description = "Tesouro Direto: preço e taxa do dia de cada título público (Selic, IPCA+, Prefixado)"
    resources = {
        "titulos": "todos os títulos na última data publicada, com taxa e preço de compra/venda",
    }

    async def fetch(self, recurso: str, **params: Any) -> NormalizedResponse:
        partes = [p for p in recurso.strip("/").split("/") if p]
        match partes:
            case ["titulos"]:
                return await self._titulos(recurso, params)
            case _:
                raise RecursoNaoEncontrado(self.name, recurso, sorted(self.resources))

    async def _titulos(self, recurso: str, params: dict) -> NormalizedResponse:
        if params:
            raise ParametroInvalido(recurso, sorted(params), [])
        # ~14 MB; a fonte é lenta e o arquivo só muda 1x por dia — o cache segura
        texto = await self.get_text(ARQUIVO, timeout=120)

        linhas = texto.splitlines()
        if not linhas or not linhas[0].startswith("Tipo Titulo"):
            raise ErroUpstream(self.name)

        # o arquivo não tem ordem: primeiro acha a data-base mais recente,
        # comparando como AAAAMMDD sem converter as ~250 mil linhas
        mais_recente = ""
        for linha in linhas[1:]:
            campos = linha.split(";")
            if len(campos) < 8:
                continue
            chave = _aaaammdd(campos[2])
            if chave > mais_recente:
                mais_recente = chave
        if not mais_recente:
            raise ErroUpstream(self.name)

        itens = []
        for linha in linhas[1:]:
            campos = linha.split(";")
            if len(campos) < 8 or _aaaammdd(campos[2]) != mais_recente:
                continue
            tipo = campos[0].strip()
            vencimento = para_data(campos[1])
            data_base = para_data(campos[2])
            if not tipo or vencimento is None or data_base is None:
                continue
            itens.append(
                TituloPublico(
                    nome=f"{tipo} {vencimento.year}",
                    tipo=tipo,
                    vencimento=vencimento,
                    data=data_base,
                    taxa_compra=valor_br(campos[3]),
                    taxa_venda=valor_br(campos[4]),
                    pu_compra=valor_br(campos[5]),
                    pu_venda=valor_br(campos[6]),
                ).model_dump(mode="json")
            )
        itens.sort(key=lambda t: (t["tipo"], t["vencimento"]))

        meta = {
            "data": date(int(mais_recente[:4]), int(mais_recente[4:6]), int(mais_recente[6:])).isoformat(),
            "fonte": FONTE,
        }
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=itens, total=len(itens), meta=meta
        )


def _aaaammdd(valor: str) -> str:
    # "01/07/2026" -> "20260701", comparável como texto; inválido -> ""
    pedacos = valor.strip().split("/")
    if len(pedacos) != 3 or not all(p.isdigit() for p in pedacos):
        return ""
    d, m, a = pedacos
    return f"{a}{m.zfill(2)}{d.zfill(2)}"
