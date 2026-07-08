"""Nota Paraná (SEFAZ-PR): menor preço praticado por estabelecimento, extraído
das NFC-e emitidas no estado. É a única fonte pública de preço REAL de balcão —
inclusive de medicamento controlado (tarja preta), que não é vendido online mas
emite nota quando vendido presencialmente. Vários estados têm um app assim; este
é o do Paraná. Goiás não tem — por isso é a peça que falta pro comparador de
remédio, e por que ele precisa de um proxy com cache na frente (esta camada)."""

from decimal import Decimal, InvalidOperation
from typing import Any

from balcao.connectors.base import BaseConnector, NormalizedResponse, register
from balcao.exceptions import ParametroInvalido, RecursoNaoEncontrado
from balcao.models import PrecoProduto
from balcao.normalize import limpa_texto, normaliza_uf

PARAMS = {"termo", "lat", "lon", "local", "raio", "offset"}

FONTE = {
    "nome": "Nota Paraná — SEFAZ-PR",
    "url": "https://menorpreco.notaparana.pr.gov.br",
    "nota": (
        "Preço praticado por loja, extraído das notas fiscais (NFC-e) do Paraná. "
        "Cobre medicamento controlado, que não aparece em e-commerce. O preço é o "
        "da última venda vista, então tem alguns dias de atraso e vale só pro PR."
    ),
}


@register
class NotaParanaConnector(BaseConnector):
    name = "notaparana"
    base_url = "https://menorpreco.notaparana.pr.gov.br/api/v1"
    description = "Nota Paraná: menor preço praticado por loja (via NFC-e), inclusive de controlado"
    resources = {
        "produtos": "preços de um produto por loja, do mais barato (params: termo = nome do produto, lat + lon = onde buscar, raio = km, offset)",
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

        local = params.get("local")
        if not local:
            lat, lon = params.get("lat"), params.get("lon")
            if not lat or not lon:
                raise ParametroInvalido(recurso, ["lat", "lon"], ["lat e lon (ou local = 'lat,lon')"])
            local = f"{lat},{lon}"

        raio = params.get("raio", 15)
        offset = params.get("offset", 0)

        bruto = await self.get_json(
            "/produtos",
            params={"local": local, "termo": termo, "raio": raio, "offset": offset},
            timeout=20,
        )
        produtos = bruto.get("produtos") or [] if isinstance(bruto, dict) else []

        itens = []
        for p in produtos:
            valor = _decimal(p.get("valor"))
            if valor is None:
                continue  # sem preço não serve
            est = p.get("estabelecimento") or {}
            endereco = " ".join(
                str(x) for x in (est.get("tp_logr"), est.get("nm_logr"), est.get("nr_logr")) if x
            ).strip()
            itens.append(
                PrecoProduto(
                    descricao=limpa_texto(p.get("desc")),
                    gtin=(p.get("gtin") or None),
                    ncm=(p.get("ncm") or None),
                    valor=valor,
                    valor_tabela=_decimal(p.get("valor_tabela")),
                    atualizado=(p.get("datahora") or None),
                    distancia_km=_float(p.get("distkm")),
                    estabelecimento=limpa_texto(est.get("nm_fan")),
                    empresa=(limpa_texto(est.get("nm_emp")) or None),
                    endereco=(endereco or None),
                    bairro=(limpa_texto(est.get("bairro")) or None),
                    municipio=(limpa_texto(est.get("mun")) or None),
                    uf=normaliza_uf(est.get("uf")),
                ).model_dump(mode="json")
            )

        total = bruto.get("total") if isinstance(bruto, dict) else None
        meta = {"termo": termo, "local": local, "raio": raio, "fonte": FONTE}
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=itens, total=total if total is not None else len(itens), meta=meta
        )


def _decimal(valor: Any) -> Decimal | None:
    # a Nota Paraná manda o preço em formato US ("1.04"), NÃO brasileiro —
    # por isso Decimal direto, e não valor_br (que trataria 1.04 como 104)
    if valor is None or valor == "":
        return None
    try:
        return Decimal(str(valor))
    except (InvalidOperation, ValueError):
        return None


def _float(valor: Any) -> float | None:
    try:
        return round(float(valor), 3)
    except (TypeError, ValueError):
        return None
