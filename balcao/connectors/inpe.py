"""INPE — Programa Queimadas: focos de incêndio no Brasil detectados por
satélite. O dataserver serve um CSV por dia (Brasil inteiro) que vai enchendo
ao longo das horas. O conector baixa o arquivo do dia e agrega os focos por
estado ou bioma — de milhares de linhas cruas pra um ranking pronto."""

import csv
import io
from datetime import date, datetime, timedelta
from typing import Any

from balcao.connectors.base import BaseConnector, NormalizedResponse, register
from balcao.exceptions import ErroUpstream, ParametroInvalido, RecursoNaoEncontrado
from balcao.models import AlertaDesmatamento, Queimada
from balcao.normalize import limpa_texto

# dimensão pedida -> coluna do CSV do INPE
DIMENSOES = {"estado": "estado", "bioma": "bioma", "municipio": "municipio"}

PARAMS = {"data", "por", "limit"}

# DETER no GeoServer do TerraBrasilis: cada bioma tem sua camada, e o pedido
# SEM geometria (propertyName) transforma megabytes de polígonos em kilobytes
WFS_URL = "https://terrabrasilis.dpi.inpe.br/geoserver/ows"
BIOMAS_DETER = {
    "amazonia": "deter-amz:deter_amz",
    "cerrado": "deter-cerrado-nb:deter_cerrado",
}
CLASSES_DETER = {
    "DESMATAMENTO_CR": "corte raso",
    "DESMATAMENTO_VEG": "desmatamento com vegetação",
    "MINERACAO": "mineração",
    "DEGRADACAO": "degradação",
    "CS_DESORDENADO": "corte seletivo desordenado",
    "CS_GEOMETRICO": "corte seletivo geométrico",
    "CICATRIZ_DE_QUEIMADA": "cicatriz de queimada",
    "aviso": "aviso",
}

FONTE_DETER = {
    "nome": "INPE — DETER (TerraBrasilis)",
    "url": "https://terrabrasilis.dpi.inpe.br/app/dashboard/alerts/legal/amazon/aggregated/",
    "nota": (
        "Alertas de desmatamento detectados por satélite, quase em tempo real. "
        "Alerta serve pra fiscalização acudir — a taxa oficial do ano é outra "
        "conta (PRODES). Nuvem esconde e alerta pequeno escapa: é piso, não teto."
    ),
}

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
        "desmatamento": (
            "alertas DETER dos últimos dias, agregados (params: bioma = amazonia|cerrado; "
            "dias = 1..90; por = uf|classe|municipio; limit)"
        ),
    }

    async def fetch(self, recurso: str, **params: Any) -> NormalizedResponse:
        partes = [p for p in recurso.strip("/").split("/") if p]
        match partes:
            case ["queimadas"] | ["focos"]:
                return await self._queimadas(recurso, params)
            case ["desmatamento"] | ["deter"]:
                return await self._desmatamento(recurso, params)
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


    async def _desmatamento(self, recurso: str, params: dict) -> NormalizedResponse:
        """Os alertas DETER dos últimos dias, agregados. O WFS devolveria
        polígono por polígono (megabytes); pedindo só os atributos e agregando
        aqui, o leitor recebe o ranking pronto."""
        aceitos = {"bioma", "dias", "por", "limit"}
        invalidos = sorted(set(params) - aceitos)
        if invalidos:
            raise ParametroInvalido(recurso, invalidos, sorted(aceitos))
        bioma = str(params.get("bioma", "amazonia")).lower()
        if bioma not in BIOMAS_DETER:
            raise ParametroInvalido(recurso, ["bioma"], sorted(BIOMAS_DETER))
        dias = str(params.get("dias", 30))
        if not dias.isdigit() or not (1 <= int(dias) <= 90):
            raise ParametroInvalido(recurso, ["dias"], ["1..90"])
        por = str(params.get("por", "uf")).lower()
        if por not in {"uf", "classe", "municipio"}:
            raise ParametroInvalido(recurso, ["por"], ["uf", "classe", "municipio"])
        limit = str(params.get("limit", 30))
        if not limit.isdigit() or not (1 <= int(limit) <= 100):
            raise ParametroInvalido(recurso, ["limit"], ["1..100"])

        inicio = date.today() - timedelta(days=int(dias))
        bruto = await self.get_json(
            WFS_URL,
            params={
                "service": "WFS",
                "version": "2.0.0",
                "request": "GetFeature",
                "typeName": BIOMAS_DETER[bioma],
                "outputFormat": "application/json",
                "count": 20000,
                "propertyName": "classname,view_date,areamunkm,municipality,uf",
                "CQL_FILTER": f"view_date AFTER {inicio.isoformat()}T00:00:00Z",
            },
            timeout=60,
        )
        feicoes = bruto.get("features", []) if isinstance(bruto, dict) else None
        if feicoes is None:
            raise ErroUpstream(self.name)

        grupos: dict[str, list[float]] = {}
        area_total = 0.0
        ultima = ""
        for f in feicoes:
            p = f.get("properties") or {}
            area = float(p.get("areamunkm") or 0)
            area_total += area
            ultima = max(ultima, p.get("view_date") or "")
            if por == "uf":
                chave = limpa_texto(p.get("uf")) or "?"
            elif por == "classe":
                cru = limpa_texto(p.get("classname")) or "?"
                chave = CLASSES_DETER.get(cru, cru.lower())
            else:
                municipio = limpa_texto(p.get("municipality")) or "?"
                chave = f"{municipio.title()} ({p.get('uf')})" if p.get("uf") else municipio.title()
            grupo = grupos.setdefault(chave, [0, 0.0])
            grupo[0] += 1
            grupo[1] += area

        itens = [
            AlertaDesmatamento(
                bioma=bioma,
                nivel=por,
                nome=nome,
                alertas=int(qtd),
                area_km2=round(area, 2),
            ).model_dump(mode="json")
            for nome, (qtd, area) in grupos.items()
        ]
        itens.sort(key=lambda i: i["area_km2"], reverse=True)
        itens = itens[: int(limit)]

        meta = {
            "bioma": bioma,
            "de": inicio.isoformat(),
            "ultima_deteccao": ultima or None,
            "alertas_total": len(feicoes),
            "area_total_km2": round(area_total, 2),
            "fonte": FONTE_DETER,
        }
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=itens, total=len(itens), meta=meta
        )

def _num(valor: Any) -> float:
    try:
        return float(valor)
    except (TypeError, ValueError):
        return 0.0
