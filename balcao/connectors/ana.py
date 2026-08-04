"""ANA (Agência Nacional de Águas), Sala de Situação/SAR: quanta água tem nos
reservatórios do país, as hidrelétricas do SIN, os açudes do Nordeste e o
Sistema Cantareira que abastece São Paulo.

A última medição sai de um endpoint JSON sem chave (o restportal, que apesar
do nome "SIN" aceita qualquer código). Já a lista de reservatórios e a série
histórica só existem nas páginas HTML do SAR: o conector parseia o dropdown e
a tabela com regex mesmo, o HTML é ASP.NET estável e as colunas mudam por
sistema, então o parse vai pelo cabeçalho, nunca pela posição."""

import asyncio
import re
from datetime import date, timedelta
from html import unescape
from typing import Any

from balcao.connectors.base import BaseConnector, NormalizedResponse, register
from balcao.exceptions import ErroUpstream, ParametroInvalido, RecursoNaoEncontrado
from balcao.models import MedicaoReservatorio, Reservatorio
from balcao.normalize import UFS, para_data, valor_br

SISTEMAS = {
    "sin": "/sar0/MedicaoSin",
    "nordeste": "/sar0/Medicao",
    "cantareira": "/sar0/MedicaoCantareira",
}

# os que todo mundo conhece: a vitrine do caderno, uma medição por chamada
PRINCIPAIS = [
    "19058",  # Itaipu
    "19121",  # Sobradinho
    "19128",  # Serra da Mesa
    "19004",  # Furnas
    "19134",  # Tucuruí
    "19119",  # Três Marias
    "19034",  # Ilha Solteira
    "19152",  # Belo Monte
    "19126",  # Xingó
    "29001",  # Jaguari-Jacareí (Cantareira)
]

OPCAO = re.compile(r'<option value="(\d+)">([^<]+)</option>')
TABELA = re.compile(r"<table[^>]*>(.*?)</table>", re.S)
LINHA = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
CELULA = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S)
UF_NO_NOME = re.compile(r"\(([A-Z]{2})\)\s*$")

FONTE = {
    "nome": "ANA, Sala de Situação (SAR)",
    "url": "https://www.ana.gov.br/sar",
    "nota": (
        "Medições diárias informadas pelos operadores dos reservatórios à "
        "Agência Nacional de Águas. Volume útil é a parte que dá pra usar; "
        "olhe a data, açude pequeno do Nordeste pode passar meses sem medição nova."
    ),
}


def _sistema_do_codigo(codigo: str) -> str:
    if codigo.startswith("29"):
        return "cantareira"
    if codigo.startswith("12"):
        return "nordeste"
    return "sin"


def _numero(valor) -> float | None:
    # o restportal manda decimal com ponto e volumeUtil como STRING ("98.32",
    # às vezes ""), float direto; valor_br aqui leria 98.32 como 9832
    if valor is None or valor == "":
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


@register
class AnaConnector(BaseConnector):
    name = "ana"
    base_url = "https://www.ana.gov.br"
    description = "ANA/SAR: volume dos reservatórios, SIN, açudes do Nordeste e Cantareira"
    resources = {
        "reservatorios": (
            "lista dos reservatórios monitorados (params: sistema = sin|nordeste|cantareira, "
            "padrão sin; uf filtra os do Nordeste; busca por trecho do nome)"
        ),
        "agora": "última medição de um reservatório (params: codigo obrigatório, pegue na lista)",
        "principais": "última medição dos grandes reservatórios do país, numa chamada só",
        "historico": "série diária de um reservatório (params: codigo obrigatório; dias = 1..90, padrão 30)",
    }

    async def fetch(self, recurso: str, **params: Any) -> NormalizedResponse:
        partes = [p for p in recurso.strip("/").split("/") if p]
        match partes:
            case ["reservatorios"]:
                return await self._reservatorios(recurso, params)
            case ["agora"]:
                return await self._agora(recurso, params)
            case ["principais"]:
                return await self._principais(recurso)
            case ["historico"]:
                return await self._historico(recurso, params)
            case _:
                raise RecursoNaoEncontrado(self.name, recurso, sorted(self.resources))

    def _codigo(self, recurso: str, params: dict) -> str:
        codigo = str(params.get("codigo", "")).strip()
        if not codigo.isdigit():
            raise ParametroInvalido(recurso, ["codigo"], ["código numérico da lista de reservatórios"])
        return codigo

    async def _reservatorios(self, recurso: str, params: dict) -> NormalizedResponse:
        invalidos = sorted(set(params) - {"sistema", "uf", "busca"})
        if invalidos:
            raise ParametroInvalido(recurso, invalidos, ["sistema", "uf", "busca"])
        sistema = str(params.get("sistema", "sin")).lower()
        if sistema not in SISTEMAS:
            raise ParametroInvalido(recurso, ["sistema"], sorted(SISTEMAS))
        uf = str(params.get("uf", "")).strip().upper()
        if uf and uf not in UFS:
            raise ParametroInvalido(recurso, ["uf"], ["sigla de UF"])
        busca = str(params.get("busca", "")).strip().casefold()

        html = await self.get_text(SISTEMAS[sistema])
        itens = []
        for codigo, cru in OPCAO.findall(html):
            if int(codigo) < 1000:  # o primeiro dropdown da página é o de estados
                continue
            nome = unescape(cru).strip()
            uf_item = None
            if achou := UF_NO_NOME.search(nome):
                uf_item = achou.group(1)
                nome = nome[: achou.start()].strip()
            if uf and uf_item != uf:
                continue
            if busca and busca not in nome.casefold():
                continue
            itens.append(
                Reservatorio(codigo=codigo, nome=nome, sistema=sistema, uf=uf_item).model_dump(mode="json")
            )

        meta = {"sistema": sistema, "fonte": FONTE}
        return NormalizedResponse(fonte=self.name, recurso=recurso, dados=itens, total=len(itens), meta=meta)

    async def _ultima(self, codigo: str) -> dict | None:
        bruto = await self.get_json("/sar/restportal/api/retornaUltimaMedicaoSIN", params={"codigo": codigo})
        if not isinstance(bruto, dict) or not bruto.get("reservatorio"):
            return None
        return MedicaoReservatorio(
            codigo=codigo,
            reservatorio=str(bruto["reservatorio"]).strip(),
            sistema=_sistema_do_codigo(codigo),
            data=para_data(bruto.get("data")),
            volume_util_pct=_numero(bruto.get("volumeUtil")),
            cota=_numero(bruto.get("cota")),
            afluencia=_numero(bruto.get("afluencia")),
            defluencia=_numero(bruto.get("defluencia")),
        ).model_dump(mode="json")

    async def _agora(self, recurso: str, params: dict) -> NormalizedResponse:
        invalidos = sorted(set(params) - {"codigo"})
        if invalidos:
            raise ParametroInvalido(recurso, invalidos, ["codigo"])
        codigo = self._codigo(recurso, params)
        item = await self._ultima(codigo)
        dados = [item] if item else []
        meta = {"codigo": codigo, "fonte": FONTE}
        return NormalizedResponse(fonte=self.name, recurso=recurso, dados=dados, total=len(dados), meta=meta)

    async def _principais(self, recurso: str) -> NormalizedResponse:
        # um reservatório fora do ar não derruba a vitrine dos outros
        medidos = await asyncio.gather(
            *(self._ultima(c) for c in PRINCIPAIS), return_exceptions=True
        )
        itens = [m for m in medidos if isinstance(m, dict)]
        if not itens:
            raise ErroUpstream(self.name)
        meta = {"pedidos": len(PRINCIPAIS), "fonte": FONTE}
        return NormalizedResponse(fonte=self.name, recurso=recurso, dados=itens, total=len(itens), meta=meta)

    async def _historico(self, recurso: str, params: dict) -> NormalizedResponse:
        invalidos = sorted(set(params) - {"codigo", "dias"})
        if invalidos:
            raise ParametroInvalido(recurso, invalidos, ["codigo", "dias"])
        codigo = self._codigo(recurso, params)
        dias = params.get("dias", 30)
        if not str(dias).isdigit() or not (1 <= int(dias) <= 90):
            raise ParametroInvalido(recurso, ["dias"], ["1..90"])
        sistema = _sistema_do_codigo(codigo)

        fim = date.today()
        inicio = fim - timedelta(days=int(dias))
        html = await self.get_text(
            SISTEMAS[sistema],
            params={
                "dropDownListEstados": "",
                "dropDownListReservatorios": codigo,
                "dataInicial": inicio.strftime("%d/%m/%Y"),
                "dataFinal": fim.strftime("%d/%m/%Y"),
                "button": "Buscar",
            },
        )
        itens = self._parse_tabela(html, codigo, sistema)
        meta = {"codigo": codigo, "de": inicio.isoformat(), "ate": fim.isoformat(), "fonte": FONTE}
        return NormalizedResponse(fonte=self.name, recurso=recurso, dados=itens, total=len(itens), meta=meta)

    @staticmethod
    def _parse_tabela(html: str, codigo: str, sistema: str) -> list[dict]:
        tabelas = TABELA.findall(html)
        if not tabelas:
            return []
        linhas = LINHA.findall(tabelas[0])
        if len(linhas) < 2:
            return []

        def celulas(linha: str) -> list[str]:
            return [unescape(re.sub(r"<[^>]+>", "", c)).strip() for c in CELULA.findall(linha)]

        # cada sistema tem sua tabela: SIN fala "Volume Útil (%)", o Nordeste
        # só "Volume (%)" (e tem "Capacidade (hm³)", que não é volume); por
        # isso o mapa vai pelo cabeçalho, nunca pela posição
        cabecalho = celulas(linhas[0])
        col = {}
        for i, titulo in enumerate(cabecalho):
            t = titulo.casefold()
            if t.startswith("reservatório"):
                col["nome"] = i
            elif t.startswith("volume") and "(%)" in t:
                col["pct"] = i
            elif t.startswith("volume") and "(hm" in t:
                col["hm3"] = i
            elif t.startswith("cota"):
                col["cota"] = i
            elif t.startswith("afluência"):
                col["afluencia"] = i
            elif t.startswith("defluência"):
                col["defluencia"] = i
            elif t.startswith("data"):
                col["data"] = i

        def pega(cels: list[str], chave: str) -> float | None:
            i = col.get(chave)
            if i is None or i >= len(cels):
                return None
            n = valor_br(cels[i])  # a tabela usa vírgula decimal
            return float(n) if n is not None else None

        itens = []
        for linha in linhas[1:]:
            cels = celulas(linha)
            if len(cels) < len(cabecalho):
                continue
            itens.append(
                MedicaoReservatorio(
                    codigo=codigo,
                    reservatorio=cels[col["nome"]] if "nome" in col else "",
                    sistema=sistema,
                    data=para_data(cels[col["data"]]) if "data" in col else None,
                    volume_util_pct=pega(cels, "pct"),
                    volume_hm3=pega(cels, "hm3"),
                    cota=pega(cels, "cota"),
                    afluencia=pega(cels, "afluencia"),
                    defluencia=pega(cels, "defluencia"),
                ).model_dump(mode="json")
            )
        return itens
