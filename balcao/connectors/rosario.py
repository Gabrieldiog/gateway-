"""Drogaria Rosário (catálogo VTEX): preço online, ao vivo, da maior rede de
farmácia do Centro-Oeste — sede em Goiânia, ~70 lojas em GO/DF/MT/TO. É a peça
que faltava pra Goiânia ter preço AO VIVO: Goiás não tem app público de NFC-e
por loja (como o Nota Paraná), mas o catálogo VTEX da rede expõe o preço
praticado do e-commerce em tempo real. NÃO cobre controlado (tarja preta não é
vendido pela internet), mas cobre a maioria dos medicamentos. Casa por GTIN/EAN
com a base do comparador."""

from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import quote

from balcao.connectors.base import BaseConnector, NormalizedResponse, register
from balcao.exceptions import ParametroInvalido, RecursoNaoEncontrado
from balcao.models import PrecoProduto
from balcao.normalize import limpa_texto

PARAMS = {"termo", "limite"}

# a API pública de busca da VTEX às vezes barra UA de datacenter; um UA de
# navegador passa limpo, e é uma chamada de leitura simples de catálogo público
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17 Safari/605.1.15"

FONTE = {
    "nome": "Drogaria Rosário (VTEX)",
    "url": "https://www.drogariarosario.com.br",
    "nota": (
        "Preço do e-commerce da rede (sede em Goiânia, líder no Centro-Oeste). "
        "É preço ao vivo, mas online — pode diferir do balcão e não cobre "
        "medicamento controlado, que não é vendido pela internet."
    ),
}


@register
class RosarioConnector(BaseConnector):
    name = "rosario"
    base_url = "https://www.drogariarosario.com.br"
    description = "Drogaria Rosário: preço online ao vivo da rede de Goiânia (catálogo VTEX)"
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

        # o ft vai no path ja encodado: um termo com espaco ("dipirona cafeina")
        # via params viraria "dipirona+cafeina" (o httpx usa "+"), e a VTEX
        # responde 400 pro "+" no full-text. Com %20 ela aceita.
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
                        gtin=(str(item["ean"]) if item.get("ean") else None),
                        valor=valor,
                        valor_tabela=tabela,
                        estabelecimento="Drogaria Rosário",
                        municipio="Goiânia",
                        uf="GO",
                    ).model_dump(mode="json")
                )
                break  # um preço por produto (o SKU principal)

        itens.sort(key=lambda d: Decimal(d["valor"]))
        meta = {"termo": termo, "fonte": FONTE}
        return NormalizedResponse(fonte=self.name, recurso=recurso, dados=itens, total=len(itens), meta=meta)


def _oferta(item: dict) -> tuple[Decimal, Decimal | None] | None:
    sellers = item.get("sellers") or []
    if not sellers:
        return None
    oferta = sellers[0].get("commertialOffer") or {}
    valor = _decimal(oferta.get("Price"))
    if valor is None or valor <= 0:
        return None
    # só serve o que dá pra comprar de fato
    disponivel = bool(oferta.get("IsAvailable", True)) and (oferta.get("AvailableQuantity") or 0) > 0
    if not disponivel:
        return None
    return valor, _decimal(oferta.get("ListPrice"))


def _decimal(valor: Any) -> Decimal | None:
    # a VTEX manda o preço como número em reais (17.91), não centavos
    if valor is None or valor == "":
        return None
    try:
        return Decimal(str(valor))
    except (InvalidOperation, ValueError):
        return None
