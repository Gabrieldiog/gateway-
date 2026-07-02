"""INPE — Programa Queimadas: focos de incêndio no Brasil detectados por
satélite. O dataserver serve um CSV por dia (Brasil inteiro) que vai enchendo
ao longo das horas. O conector baixa o arquivo do dia e agrega os focos por
estado ou bioma — de milhares de linhas cruas pra um ranking pronto."""

import csv
import io
from datetime import date, datetime
from typing import Any

from balcao.connectors.base import BaseConnector, NormalizedResponse, register
from balcao.exceptions import ParametroInvalido, RecursoNaoEncontrado
from balcao.models import Queimada
from balcao.normalize import limpa_texto

# dimensão pedida -> coluna do CSV do INPE
DIMENSOES = {"estado": "estado", "bioma": "bioma", "municipio": "municipio"}

PARAMS = {"data", "por", "limit"}

FONTE = {
    "nome": "INPE — Programa Queimadas",
    "url": "https://terrabrasilis.dpi.inpe.br/queimadas/portal/",
    "nota": (
        "Focos de incêndio detectados por satélite e consolidados pelo INPE. O "
        "arquivo do dia é atualizado ao longo das horas; um foco é um pixel quente, "
        "não necessariamente um incêndio distinto. FRP = potência radiativa do fogo."
    ),
}


@register
class InpeConnector(BaseConnector):
    name = "inpe"
    base_url = "https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/diario/Brasil"
    description = "INPE Programa Queimadas: focos de incêndio no Brasil por estado e bioma (atualiza no dia)"
    resources = {
        "queimadas": "focos de incêndio do dia agregados (params: por=estado|bioma|municipio, data=YYYY-MM-DD, limit)",
    }

    async def fetch(self, recurso: str, **params: Any) -> NormalizedResponse:
        partes = [p for p in recurso.strip("/").split("/") if p]
        match partes:
            case ["queimadas"] | ["focos"]:
                return await self._queimadas(recurso, params)
            case _:
                raise RecursoNaoEncontrado(self.name, recurso, sorted(self.resources))

    async def _queimadas(self, recurso: str, params: dict) -> NormalizedResponse:
        invalidos = sorted(set(params) - PARAMS)
        if invalidos:
            raise ParametroInvalido(recurso, invalidos, sorted(PARAMS))

        por = str(params.get("por", "estado"))
        if por not in DIMENSOES:
            raise ParametroInvalido(recurso, ["por"], sorted(DIMENSOES))
        coluna = DIMENSOES[por]

        dia = self._data(recurso, params.get("data"))
        limit = self._limit(recurso, params.get("limit"))

        # o arquivo diário chega a ~1 MB; o INPE às vezes demora, deixa esticar
        texto = await self.get_text(f"/focos_diario_br_{dia:%Y%m%d}.csv", timeout=45)

        focos: dict[str, int] = {}
        frp: dict[str, float] = {}
        total = 0
        for linha in csv.DictReader(io.StringIO(texto)):
            nome = limpa_texto(linha.get(coluna)) or "—"
            focos[nome] = focos.get(nome, 0) + 1
            frp[nome] = frp.get(nome, 0.0) + _num(linha.get("frp"))
            total += 1

        ranking = sorted(focos.items(), key=lambda kv: kv[1], reverse=True)[:limit]
        dados = [
            Queimada(
                data=dia, nivel=por, nome=nome, focos=n, frp_total=round(frp[nome], 1)
            ).model_dump(mode="json")
            for nome, n in ranking
        ]
        meta = {
            "data": dia.isoformat(),
            "por": por,
            "total_focos": total,
            "fonte": FONTE,
        }
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=dados, total=len(dados), meta=meta
        )

    def _data(self, recurso: str, valor: Any) -> date:
        if not valor:
            return date.today()
        try:
            return datetime.strptime(str(valor), "%Y-%m-%d").date()
        except ValueError:
            raise ParametroInvalido(recurso, ["data"], ["YYYY-MM-DD"]) from None

    def _limit(self, recurso: str, valor: Any) -> int:
        if valor is None:
            return 27
        if not str(valor).isdigit() or not (1 <= int(valor) <= 200):
            raise ParametroInvalido(recurso, ["limit"], ["1..200"])
        return int(valor)


def _num(valor: Any) -> float:
    try:
        return float(valor)
    except (TypeError, ValueError):
        return 0.0
