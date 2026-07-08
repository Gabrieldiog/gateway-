"""Conector VTEX genérico: várias redes de farmácia rodam na MESMA plataforma
(VTEX), com o mesmo endpoint público de catálogo. Então o conector é um só,
parametrizado por host — plugar uma rede nova é escrever uma subclasse com o
domínio e como rotular o preço. Casa por GTIN/EAN com a base do comparador.

O preço do canal padrão da VTEX é o do e-commerce, que pode diferir do balcão.
Cada rede declara `preco_tipo`:
- local: tem loja física na cidade; o preço online reflete a praça (Rosário, Alexfarma em Goiânia)
- nacional_entregavel: preço nacional do e-commerce, mas entrega na cidade (Extrafarma)
- referencia: só comparação, entrega incerta
"""

from abc import ABC
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import quote

from balcao.connectors.base import BaseConnector, NormalizedResponse, register
from balcao.exceptions import ParametroInvalido, RecursoNaoEncontrado
from balcao.models import PrecoProduto
from balcao.normalize import limpa_texto

PARAMS = {"termo", "limite"}

# a API pública de busca da VTEX às vezes barra UA de datacenter; um UA de
# navegador passa limpo, e é uma leitura simples de catálogo público
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17 Safari/605.1.15"


class VtexConnector(BaseConnector, ABC):
    """Base das redes VTEX. A subclasse define name, base_url e como se apresenta
    (rede_nome, municipio, uf, preco_tipo, fonte_nota)."""

    rede_nome: str  # nome amigável da rede (vai no estabelecimento)
    municipio: str | None = None
    uf: str | None = None
    preco_tipo: str = "referencia"
    fonte_nota: str = ""
    resources = {
        "produtos": "preços de um produto no catálogo da rede, do mais barato (params: termo = nome do produto, limite)",
    }

    async def fetch(self, recurso: str, **params: Any) -> NormalizedResponse:
        partes = [p for p in recurso.strip("/").split("/") if p]
        match partes:
            case ["produtos"]:
                return await self._produtos(recurso, params)
            case _:
                raise RecursoNaoEncontrado(self.name, recurso, sorted(self.resources))

    async def _produtos(self, recurso: str, params: dict) -> NormalizedResponse:
        invalidos = sorted(set(params) - PARAMS)
        if invalidos:
            raise ParametroInvalido(recurso, invalidos, sorted(PARAMS))

        termo = str(params.get("termo", "")).strip()
        if not termo:
            raise ParametroInvalido(recurso, ["termo"], ["termo = nome do produto"])

        try:
            limite = max(1, min(int(params.get("limite", 20)), 50))
        except (TypeError, ValueError):
            limite = 20

        # o ft vai no path já encodado: um termo com espaço via params viraria
        # "dipirona+cafeina" (o httpx usa "+"), e a VTEX responde 400 pro "+".
        ft = quote(termo, safe="")
        bruto = await self.get_json(
            f"/api/catalog_system/pub/products/search/?ft={ft}&_from=0&_to={limite - 1}",
            timeout=20,
            headers={"User-Agent": UA, "Accept": "application/json"},
        )
        produtos = bruto if isinstance(bruto, list) else []

        itens = []
        for p in produtos:
            for item in p.get("items") or []:
                oferta = _oferta(item)
                if oferta is None:
                    continue  # sem preço ou fora de estoque não serve
                valor, tabela = oferta
                itens.append(
                    PrecoProduto(
                        fonte=self.name,
                        descricao=limpa_texto(item.get("nameComplete") or p.get("productName")),
                        gtin=_gtin(item),
                        valor=valor,
                        valor_tabela=tabela,
                        estabelecimento=self.rede_nome,
                        municipio=self.municipio,
                        uf=self.uf,
                        preco_tipo=self.preco_tipo,
                    ).model_dump(mode="json")
                )
                break  # um preço por produto (o SKU principal)

        itens.sort(key=lambda d: Decimal(d["valor"]))
        meta = {
            "termo": termo,
            "fonte": {"nome": self.rede_nome, "url": self.base_url, "preco_tipo": self.preco_tipo, "nota": self.fonte_nota},
        }
        return NormalizedResponse(fonte=self.name, recurso=recurso, dados=itens, total=len(itens), meta=meta)


@register
class RosarioConnector(VtexConnector):
    name = "rosario"
    base_url = "https://www.drogariarosario.com.br"
    description = "Drogaria Rosário: preço online ao vivo da rede de Goiânia (catálogo VTEX)"
    rede_nome = "Drogaria Rosário"
    municipio = "Goiânia"
    uf = "GO"
    preco_tipo = "local"
    fonte_nota = "Preço do e-commerce da rede (sede em Goiânia) — é preço de internet e pode diferir do balcão."


@register
class AlexfarmaConnector(VtexConnector):
    name = "alexfarma"
    base_url = "https://www.alexfarma.com.br"
    description = "Alexfarma: preço online da rede goiana (catálogo VTEX) — preço local de Goiânia"
    rede_nome = "Alexfarma"
    municipio = "Goiânia"
    uf = "GO"
    preco_tipo = "local"
    fonte_nota = "Rede com loja em Goiânia que entrega na cidade — o preço online reflete a praça."


@register
class ExtrafarmaConnector(VtexConnector):
    name = "extrafarma"
    base_url = "https://www.extrafarma.com.br"
    description = "Extrafarma: e-commerce nacional (grupo Pague Menos) que entrega em Goiânia (catálogo VTEX)"
    rede_nome = "Extrafarma"
    preco_tipo = "nacional_entregavel"
    fonte_nota = "Preço do e-commerce nacional; entrega em Goiânia, mas pode diferir do balcão de uma loja física."


def _oferta(item: dict) -> tuple[Decimal, Decimal | None] | None:
    sellers = item.get("sellers") or []
    if not sellers:
        return None
    oferta = sellers[0].get("commertialOffer") or {}
    valor = _decimal(oferta.get("Price"))
    if valor is None or valor <= 0:
        return None
    disponivel = bool(oferta.get("IsAvailable", True)) and (oferta.get("AvailableQuantity") or 0) > 0
    if not disponivel:
        return None
    return valor, _decimal(oferta.get("ListPrice"))


def _gtin(item: dict) -> str | None:
    # a VTEX às vezes manda "SEM GTIN" ou um código de kit ("KITPGM-20001") no
    # campo ean; só serve pra casar com a base o que parece EAN de verdade
    ean = str(item.get("ean") or "").strip()
    return ean if ean.isdigit() and 8 <= len(ean) <= 14 else None


def _decimal(valor: Any) -> Decimal | None:
    # a VTEX manda o preço como número em reais (17.91), não centavos
    if valor is None or valor == "":
        return None
    try:
        return Decimal(str(valor))
    except (InvalidOperation, ValueError):
        return None
