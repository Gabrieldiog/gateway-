"""Educação (INEP, servido pela API de Pesquisas do IBGE): a nota do IDEB e o
tamanho da rede de ensino de cada município, ano a ano. O INEP não tem API de
consulta — mas o IBGE republica IDEB (pesquisa 40) e Censo Escolar (pesquisa
13) num JSON limpo por município. Cada indicador é uma chamada; o conector
dispara as etapas em paralelo e devolve a série pronta.

Quirks: os nós agregadores da árvore devolvem lista vazia (só os indicadores
de rede/etapa têm dado), o valor ausente vem como "-" (vira None), e a resposta
chega comprimida (o httpx descomprime sozinho)."""

import asyncio
from typing import Any

from balcao.connectors.base import BaseConnector, NormalizedResponse, register
from balcao.exceptions import ErroUpstream, ParametroInvalido, RecursoNaoEncontrado
from balcao.models import IndicadorEducacao

# IDEB (pesquisa 40): cada etapa tem um indicador por rede de ensino
IDEB = {
    "iniciais": {"publica": "78187", "municipal": "78188", "estadual": "78189", "federal": "78190", "privada": "78191"},
    "finais": {"publica": "78192", "municipal": "78193", "estadual": "78194", "federal": "78195", "privada": "78196"},
    "medio": {"publica": "78197", "municipal": "78198", "estadual": "78199", "federal": "78200", "privada": "78201"},
}
ETAPAS_IDEB = {
    "iniciais": "Anos iniciais (1º ao 5º)",
    "finais": "Anos finais (6º ao 9º)",
    "medio": "Ensino médio",
}
REDES = {"publica", "municipal", "estadual", "federal", "privada"}

# Censo Escolar (pesquisa 13): matrículas, docentes e escolas por etapa
CENSO = {
    "matriculas": {"infantil": "77881", "fundamental": "5908", "medio": "5913"},
    "docentes": {"infantil": "77887", "fundamental": "5929", "medio": "5934"},
    "escolas": {"infantil": "77893", "fundamental": "5950", "medio": "5955"},
}
ETAPAS_CENSO = {"infantil": "Educação infantil", "fundamental": "Ensino fundamental", "medio": "Ensino médio"}

FONTE = {
    "nome": "INEP — IDEB e Censo Escolar (via IBGE)",
    "url": "https://www.gov.br/inep/pt-br/areas-de-atuacao/pesquisas-estatisticas-e-indicadores/ideb",
    "nota": (
        "O IDEB combina aprovação e nota da Prova Brasil numa escala de 0 a 10 e "
        "sai a cada dois anos; o Censo Escolar conta matrículas, docentes e escolas "
        "todo ano. Traço no lugar da nota quer dizer que o INEP não divulgou aquele ano."
    ),
}


def _numero(valor: Any) -> float | None:
    # IDEB vem "5.9", matrícula vem "1334975"; ausência vem "-" ou ".."
    if valor in (None, "", "-", ".."):
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


@register
class EducacaoConnector(BaseConnector):
    name = "educacao"
    base_url = "https://servicodados.ibge.gov.br/api/v1/pesquisas"
    description = "INEP: IDEB e Censo Escolar (matrículas, docentes, escolas) por município"
    resources = {
        "ideb": (
            "a nota do IDEB de um município, por etapa, ano a ano "
            "(params: municipio = código IBGE; rede = publica|municipal|estadual|federal|privada)"
        ),
        "censo": (
            "o tamanho da rede de ensino de um município (params: municipio = código IBGE; "
            "tema = matriculas|docentes|escolas)"
        ),
    }

    async def fetch(self, recurso: str, **params: Any) -> NormalizedResponse:
        partes = [p for p in recurso.strip("/").split("/") if p]
        match partes:
            case ["ideb"]:
                return await self._ideb(recurso, params)
            case ["censo"]:
                return await self._censo(recurso, params)
            case _:
                raise RecursoNaoEncontrado(self.name, recurso, sorted(self.resources))

    def _municipio(self, recurso: str, params: dict) -> str:
        codigo = str(params.get("municipio", "")).strip()
        if not (codigo.isdigit() and len(codigo) == 7):
            raise ParametroInvalido(recurso, ["municipio"], ["código IBGE do município (7 dígitos)"])
        return codigo

    async def _serie(self, pesquisa: str, indicador: str, municipio: str) -> tuple[list[dict], int | None, float | None]:
        """Baixa um indicador e devolve a série (ano->valor) já limpa e ordenada."""
        bruto = await self.get_json(
            f"/{pesquisa}/indicadores/{indicador}/resultados/{municipio}", timeout=30
        )
        if not isinstance(bruto, list) or not bruto:
            return [], None, None
        resultados = bruto[0].get("res") or []
        if not resultados:
            return [], None, None
        por_ano = resultados[0].get("res") or {}
        serie = []
        for ano, valor in por_ano.items():
            num = _numero(valor)
            if num is not None:
                serie.append({"ano": int(ano), "valor": num})
        serie.sort(key=lambda p: p["ano"])
        if not serie:
            return [], None, None
        ultimo = serie[-1]
        return serie, ultimo["ano"], ultimo["valor"]

    async def _ideb(self, recurso: str, params: dict) -> NormalizedResponse:
        invalidos = sorted(set(params) - {"municipio", "rede"})
        if invalidos:
            raise ParametroInvalido(recurso, invalidos, ["municipio", "rede"])
        municipio = self._municipio(recurso, params)
        rede = str(params.get("rede", "publica")).lower()
        if rede not in REDES:
            raise ParametroInvalido(recurso, ["rede"], sorted(REDES))

        etapas = list(IDEB)
        series = await asyncio.gather(
            *(self._serie("40", IDEB[etapa][rede], municipio) for etapa in etapas),
            return_exceptions=True,
        )
        if all(isinstance(s, BaseException) for s in series):
            raise ErroUpstream(self.name)
        itens = []
        for etapa, resultado in zip(etapas, series):
            if isinstance(resultado, BaseException):
                continue
            serie, ultimo_ano, ultimo_valor = resultado
            itens.append(
                IndicadorEducacao(
                    municipio=municipio, tema="ideb", etapa=ETAPAS_IDEB[etapa],
                    rede=rede, serie=serie, ultimo_ano=ultimo_ano, ultimo_valor=ultimo_valor,
                ).model_dump(mode="json")
            )
        meta = {"municipio": municipio, "rede": rede, "fonte": FONTE}
        return NormalizedResponse(fonte=self.name, recurso=recurso, dados=itens, total=len(itens), meta=meta)

    async def _censo(self, recurso: str, params: dict) -> NormalizedResponse:
        invalidos = sorted(set(params) - {"municipio", "tema"})
        if invalidos:
            raise ParametroInvalido(recurso, invalidos, ["municipio", "tema"])
        municipio = self._municipio(recurso, params)
        tema = str(params.get("tema", "matriculas")).lower()
        if tema not in CENSO:
            raise ParametroInvalido(recurso, ["tema"], sorted(CENSO))

        etapas = list(CENSO[tema])
        series = await asyncio.gather(
            *(self._serie("13", CENSO[tema][etapa], municipio) for etapa in etapas),
            return_exceptions=True,
        )
        if all(isinstance(s, BaseException) for s in series):
            raise ErroUpstream(self.name)
        itens = []
        for etapa, resultado in zip(etapas, series):
            if isinstance(resultado, BaseException):
                continue
            serie, ultimo_ano, ultimo_valor = resultado
            itens.append(
                IndicadorEducacao(
                    municipio=municipio, tema=tema, etapa=ETAPAS_CENSO[etapa],
                    serie=serie, ultimo_ano=ultimo_ano, ultimo_valor=ultimo_valor,
                ).model_dump(mode="json")
            )
        meta = {"municipio": municipio, "tema": tema, "fonte": FONTE}
        return NormalizedResponse(fonte=self.name, recurso=recurso, dados=itens, total=len(itens), meta=meta)
