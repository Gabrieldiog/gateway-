"""Banco Mundial: o Brasil comparado com o resto do planeta. A API v2 é
aberta e multi-país ("BRA;ARG;CHL" numa URL só), e mrv=N devolve os N valores
mais recentes de cada país — o comparador inteiro sai numa chamada. Quirks:
parte das respostas chega com BOM UTF-8 na frente do JSON (o parse tolera),
a resposta é um array [metadados, dados], e ano sem medição vem value=null."""

import asyncio
import json
from typing import Any

from balcao.connectors.base import BaseConnector, NormalizedResponse, register
from balcao.exceptions import ErroUpstream, ParametroInvalido, RecursoNaoEncontrado
from balcao.models import IndicadorMundial
from balcao.normalize import limpa_texto

# apelido -> (código no Banco Mundial, rótulo, unidade)
INDICADORES = {
    "pib-per-capita": ("NY.GDP.PCAP.CD", "PIB per capita", "US$ correntes"),
    "expectativa-vida": ("SP.DYN.LE00.IN", "Expectativa de vida", "anos"),
    "desemprego": ("SL.UEM.TOTL.ZS", "Desemprego", "% da força de trabalho"),
    "inflacao": ("FP.CPI.TOTL.ZG", "Inflação ao consumidor", "% ao ano"),
    "gini": ("SI.POV.GINI", "Desigualdade (Gini)", "0–100, maior = mais desigual"),
    "mortalidade-infantil": ("SP.DYN.IMRT.IN", "Mortalidade infantil", "por mil nascidos vivos"),
    "internet": ("IT.NET.USER.ZS", "Pessoas na internet", "% da população"),
    "co2": ("EN.GHG.CO2.PC.CE.AR5", "CO₂ per capita", "toneladas por ano"),
}

PAISES = {
    "brasil": "BRA", "argentina": "ARG", "chile": "CHL", "colombia": "COL",
    "mexico": "MEX", "uruguai": "URY", "paraguai": "PRY", "bolivia": "BOL",
    "peru": "PER", "venezuela": "VEN", "eua": "USA", "estados-unidos": "USA",
    "china": "CHN", "india": "IND", "russia": "RUS", "africa-do-sul": "ZAF",
    "portugal": "PRT", "espanha": "ESP", "franca": "FRA", "alemanha": "DEU",
    "italia": "ITA", "reino-unido": "GBR", "japao": "JPN", "coreia-do-sul": "KOR",
    "canada": "CAN", "australia": "AUS", "mundo": "WLD",
}

PADRAO_COMPARAR = "brasil,argentina,chile,colombia,mexico,eua,china,india"

FONTE = {
    "nome": "Banco Mundial — World Development Indicators",
    "url": "https://data.worldbank.org",
    "nota": (
        "Indicadores comparáveis entre países, compilados pelo Banco Mundial a "
        "partir das estatísticas oficiais de cada um. Cada país mede no seu ritmo — "
        "o ano ao lado do valor diz de quando é o dado."
    ),
}


@register
class MundoConnector(BaseConnector):
    name = "mundo"
    base_url = "https://api.worldbank.org/v2"
    description = "Banco Mundial: o Brasil comparado com o mundo — PIB, vida, desemprego, CO₂"
    resources = {
        "comparar": (
            f"o último valor de um indicador em vários países numa chamada "
            f"(params: indicador = {'|'.join(sorted(INDICADORES))} ou código do Banco Mundial; "
            "paises = lista separada por vírgula, apelidos ou ISO3)"
        ),
        "serie": "a evolução de um indicador num país (params: indicador; pais, padrão brasil; ultimos = 1..60)",
        "painel": "o Brasil nos 8 indicadores-chave, com o ano de cada medição",
    }

    async def fetch(self, recurso: str, **params: Any) -> NormalizedResponse:
        partes = [p for p in recurso.strip("/").split("/") if p]
        match partes:
            case ["comparar"]:
                return await self._comparar(recurso, params)
            case ["serie"]:
                return await self._serie(recurso, params)
            case ["painel"]:
                return await self._painel(recurso, params)
            case _:
                raise RecursoNaoEncontrado(self.name, recurso, sorted(self.resources))

    async def _wb(self, caminho: str, consulta: dict) -> list:
        # parte das respostas vem com BOM UTF-8 antes do JSON — o json() padrão
        # engasga, então o parse é manual e tolerante
        texto = await self.get_text(caminho, params={"format": "json", **consulta}, timeout=40)
        try:
            bruto = json.loads(texto.lstrip("﻿"))
        except ValueError as exc:
            raise ErroUpstream(self.name) from exc
        if not isinstance(bruto, list) or len(bruto) < 2:
            # indicador inexistente volta [{"message": [...]}]
            raise ParametroInvalido(caminho, ["indicador"], sorted(INDICADORES))
        return bruto[1] or []

    def _indicador(self, recurso: str, params: dict) -> tuple[str, str, str]:
        pedido = str(params.get("indicador", "")).strip()
        if not pedido:
            raise ParametroInvalido(recurso, ["indicador"], sorted(INDICADORES))
        if pedido.lower() in INDICADORES:
            return INDICADORES[pedido.lower()]
        # código cru do Banco Mundial (ex NY.GDP.MKTP.CD) também vale
        if all(parte.isalnum() for parte in pedido.split(".")) and "." in pedido:
            return pedido.upper(), pedido.upper(), ""
        raise ParametroInvalido(recurso, ["indicador"], sorted(INDICADORES))

    def _paises(self, recurso: str, params: dict, padrao: str) -> list[str]:
        pedidos = [p.strip().lower() for p in str(params.get("paises", padrao)).split(",") if p.strip()]
        if not pedidos or len(pedidos) > 12:
            raise ParametroInvalido(recurso, ["paises"], ["1 a 12 países"])
        iso = []
        for p in pedidos:
            if p in PAISES:
                iso.append(PAISES[p])
            elif len(p) == 3 and p.isalpha():
                iso.append(p.upper())
            else:
                raise ParametroInvalido(recurso, [f"paises={p}"], sorted(PAISES))
        return iso

    def _monta(self, linha: dict, rotulo: str, unidade: str) -> dict | None:
        if linha.get("value") is None:
            return None
        return IndicadorMundial(
            indicador=rotulo,
            codigo=(linha.get("indicator") or {}).get("id", ""),
            unidade=unidade or limpa_texto((linha.get("indicator") or {}).get("value")) or "",
            pais=limpa_texto((linha.get("country") or {}).get("value")) or "?",
            iso3=str(linha.get("countryiso3code") or ""),
            ano=int(linha.get("date") or 0),
            valor=float(linha["value"]),
        ).model_dump(mode="json")

    async def _comparar(self, recurso: str, params: dict) -> NormalizedResponse:
        invalidos = sorted(set(params) - {"indicador", "paises"})
        if invalidos:
            raise ParametroInvalido(recurso, invalidos, ["indicador", "paises"])
        codigo, rotulo, unidade = self._indicador(recurso, params)
        paises = self._paises(recurso, params, PADRAO_COMPARAR)
        linhas = await self._wb(
            f"/country/{';'.join(paises)}/indicator/{codigo}",
            {"mrv": 1, "per_page": 100},
        )
        itens = [m for linha in linhas if (m := self._monta(linha, rotulo, unidade))]
        itens.sort(key=lambda i: i["valor"], reverse=True)
        meta = {"indicador": rotulo, "codigo": codigo, "paises": paises, "fonte": FONTE}
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=itens, total=len(itens), meta=meta
        )

    async def _serie(self, recurso: str, params: dict) -> NormalizedResponse:
        invalidos = sorted(set(params) - {"indicador", "pais", "ultimos"})
        if invalidos:
            raise ParametroInvalido(recurso, invalidos, ["indicador", "pais", "ultimos"])
        codigo, rotulo, unidade = self._indicador(recurso, params)
        ultimos = str(params.get("ultimos", 25))
        if not ultimos.isdigit() or not (1 <= int(ultimos) <= 60):
            raise ParametroInvalido(recurso, ["ultimos"], ["1..60"])
        pais = self._paises(recurso, {"paises": str(params.get("pais", "brasil"))}, "brasil")[0]
        linhas = await self._wb(
            f"/country/{pais}/indicator/{codigo}", {"mrv": int(ultimos), "per_page": 100}
        )
        itens = [m for linha in linhas if (m := self._monta(linha, rotulo, unidade))]
        itens.sort(key=lambda i: i["ano"])
        meta = {"indicador": rotulo, "codigo": codigo, "pais": pais, "fonte": FONTE}
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=itens, total=len(itens), meta=meta
        )

    async def _painel(self, recurso: str, params: dict) -> NormalizedResponse:
        if params:
            raise ParametroInvalido(recurso, sorted(params), [])

        async def um(apelido: str):
            codigo, rotulo, unidade = INDICADORES[apelido]
            linhas = await self._wb(f"/country/BRA/indicator/{codigo}", {"mrv": 1})
            return self._monta(linhas[0], rotulo, unidade) if linhas else None

        medidos = await asyncio.gather(*(um(a) for a in INDICADORES), return_exceptions=True)
        itens = [m for m in medidos if isinstance(m, dict)]
        if not itens:
            raise ErroUpstream(self.name)
        meta = {"pais": "BRA", "pedidos": len(INDICADORES), "fonte": FONTE}
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=itens, total=len(itens), meta=meta
        )
