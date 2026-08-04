"""Farmácias Nissei (plataforma RetailON/Inteliger, NÃO é VTEX): a rede com mais
lojas físicas em Goiânia (uma 24h). Prova que o mesmo contrato de conector cobre
uma plataforma diferente da VTEX, a graça do gateway. O fluxo tem 3 passos: pega
o token CSRF na home, busca os produtos (índice Elasticsearch) e pega os preços
num segundo POST. Preço do site da rede, que tem loja em Goiânia (preco_tipo local)."""

from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from balcao.connectors.base import BaseConnector, NormalizedResponse, register
from balcao.exceptions import ErroUpstream, ParametroInvalido, RecursoNaoEncontrado
from balcao.models import PrecoProduto
from balcao.normalize import limpa_texto

PARAMS = {"termo", "limite"}
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17 Safari/605.1.15"

FONTE = {
    "nome": "Farmácias Nissei",
    "url": "https://www.farmaciasnissei.com.br",
    "preco_tipo": "local",
    "nota": "Preço do site da rede (RetailON), que tem lojas em Goiânia; é preço de internet e pode diferir do balcão.",
}


@register
class NisseiConnector(BaseConnector):
    name = "nissei"
    base_url = "https://www.farmaciasnissei.com.br"
    description = "Farmácias Nissei: preço online da rede (plataforma RetailON), com lojas em Goiânia"
    resources = {
        "produtos": "preços de um produto no site da rede, do mais barato (params: termo = nome do produto, limite)",
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

        if self.breaker.aberto:
            raise ErroUpstream(self.name, circuito_aberto=True, tente_em_s=max(1, round(self.breaker.restante)))

        try:
            produtos, precos = await self._busca_e_precos(termo, limite)
        except httpx.HTTPError as exc:
            self.breaker.registra_falha()
            raise ErroUpstream(self.name) from exc
        self.breaker.registra_sucesso()

        itens = []
        for s in produtos:
            info = (precos.get(str(s.get("cd_produto"))) or {}).get("publico") or {}
            valor = _decimal(info.get("valor_fim") or info.get("valor_ini"))
            if valor is None or valor <= 0 or not info.get("is_disponivel", True):
                continue
            itens.append(
                PrecoProduto(
                    fonte=self.name,
                    descricao=limpa_texto(s.get("nm_produto")),
                    valor=valor,
                    valor_tabela=_decimal(info.get("valor_ini")),
                    estabelecimento="Farmácias Nissei",
                    municipio="Goiânia",
                    uf="GO",
                    preco_tipo="local",
                ).model_dump(mode="json")
            )

        itens.sort(key=lambda d: Decimal(d["valor"]))
        meta = {"termo": termo, "fonte": FONTE}
        return NormalizedResponse(fonte=self.name, recurso=recurso, dados=itens, total=len(itens), meta=meta)

    async def _busca_e_precos(self, termo: str, limite: int) -> tuple[list[dict], dict]:
        # 1) token CSRF na home (a plataforma exige double-submit: cookie + header)
        home = await self.client.get(self.base_url + "/", headers={"User-Agent": UA}, timeout=20, follow_redirects=True)
        home.raise_for_status()
        csrf = self.client.cookies.get("csrftoken")
        if not csrf:
            raise httpx.HTTPError("sem csrftoken")
        hdr = {"User-Agent": UA, "Referer": self.base_url + "/", "X-Requested-With": "XMLHttpRequest", "X-CSRFToken": csrf}

        # 2) busca no índice (Elasticsearch) -> lista de produtos com cd_produto
        busca = await self.client.post(
            self.base_url + "/pesquisa/pesquisar",
            data={"termo": termo, "pagina": "1"},
            headers=hdr,
            timeout=20,
        )
        busca.raise_for_status()
        achados = (busca.json() or {}).get("produtos") or []
        produtos = [(a.get("_source") or {}) for a in achados[:limite]]
        produtos = [s for s in produtos if s.get("cd_produto") and s.get("is_disponivel")]
        if not produtos:
            return [], {}

        # 3) preços dos produtos achados, num POST só
        ids = [str(s["cd_produto"]) for s in produtos]
        resp = await self.client.post(
            self.base_url + "/pegar/preco",
            data={"produtos_ids[]": ids, "csrfmiddlewaretoken": csrf},
            headers=hdr,
            timeout=20,
        )
        resp.raise_for_status()
        precos = (resp.json() or {}).get("precos") or {}
        return produtos, precos


def _decimal(valor: Any) -> Decimal | None:
    # o RetailON manda o preço como string em reais ("9.29"), não centavos
    if valor is None or valor == "":
        return None
    try:
        return Decimal(str(valor))
    except (InvalidOperation, ValueError):
        return None
