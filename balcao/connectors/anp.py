"""ANP: o preço dos combustíveis nos postos, do levantamento semanal oficial.
Não há API; são CSVs rolantes das últimas quatro semanas, posto a posto
(~80 mil coletas), atrás de um firewall que devolve 403 pra User-Agent que
não pareça navegador. O conector baixa, agrega por estado ou município e
devolve preço médio, mínimo e máximo; do jeito que a pergunta é feita:
"quanto tá a gasolina?"."""

import csv
import io
from decimal import Decimal
from typing import Any

from balcao.connectors.base import BaseConnector, NormalizedResponse, register
from balcao.exceptions import ErroUpstream, ParametroInvalido, RecursoNaoEncontrado
from balcao.models import PrecoCombustivel
from balcao.normalize import limpa_texto, normaliza_uf, valor_br

# slug amigável -> (arquivo rolante, nome oficial do produto na fonte)
COMBUSTIVEIS = {
    "gasolina": ("gasolina-etanol", "GASOLINA"),
    "gasolina-aditivada": ("gasolina-etanol", "GASOLINA ADITIVADA"),
    "etanol": ("gasolina-etanol", "ETANOL"),
    "diesel": ("diesel-gnv", "DIESEL"),
    "diesel-s10": ("diesel-gnv", "DIESEL S10"),
    "gnv": ("diesel-gnv", "GNV"),
    "glp": ("glp", "GLP"),
}

PARAMS = {"combustivel", "por", "uf", "limit"}

# o firewall do gov.br barra cliente que não pareça navegador: 403 pra
# User-Agent técnico E 401 pro Accept: application/json que o client
# compartilhado usa (necessário pro Senado): aqui os dois são sobrescritos
CABECALHOS_NAVEGADOR = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    ),
    "Accept": "*/*",
}

FONTE = {
    "nome": "ANP, Levantamento de Preços de Combustíveis",
    "url": "https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/precos",
    "nota": (
        "Pesquisa semanal da ANP nos postos, janela das últimas quatro semanas. "
        "O preço médio é a média simples das coletas, o do seu posto pode variar."
    ),
}


@register
class AnpConnector(BaseConnector):
    name = "anp"
    base_url = "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos/shpc"
    description = "ANP: preço de gasolina, etanol, diesel, GNV e GLP por estado e município (pesquisa semanal)"
    resources = {
        "precos": (
            f"preço médio agregado (params: combustivel = {', '.join(sorted(COMBUSTIVEIS))}; "
            "por = estado|municipio; uf; limit)"
        ),
    }

    async def fetch(self, recurso: str, **params: Any) -> NormalizedResponse:
        partes = [p for p in recurso.strip("/").split("/") if p]
        match partes:
            case ["precos"]:
                return await self._precos(recurso, params)
            case _:
                raise RecursoNaoEncontrado(self.name, recurso, sorted(self.resources))

    async def _precos(self, recurso: str, params: dict) -> NormalizedResponse:
        invalidos = sorted(set(params) - PARAMS)
        if invalidos:
            raise ParametroInvalido(recurso, invalidos, sorted(PARAMS))

        combustivel = str(params.get("combustivel", "gasolina")).lower()
        if combustivel not in COMBUSTIVEIS:
            raise ParametroInvalido(recurso, ["combustivel"], sorted(COMBUSTIVEIS))
        por = str(params.get("por", "estado")).lower()
        if por not in {"estado", "municipio"}:
            raise ParametroInvalido(recurso, ["por"], ["estado", "municipio"])
        uf = normaliza_uf(params.get("uf")) if params.get("uf") else None
        if params.get("uf") and uf is None:
            raise ParametroInvalido(recurso, ["uf"], ["sigla de UF válida"])
        limit = params.get("limit", 27 if por == "estado" else 40)
        if not str(limit).isdigit() or not (1 <= int(limit) <= 200):
            raise ParametroInvalido(recurso, ["limit"], ["1..200"])

        arquivo, produto = COMBUSTIVEIS[combustivel]
        texto = await self.get_text(
            f"/qus/ultimas-4-semanas-{arquivo}.csv",
            timeout=90,
            headers=CABECALHOS_NAVEGADOR,
        )

        # o CSV tem BOM, campo com ';' embutido entre aspas e vírgula decimal,
        # parser de verdade, não split
        grupos: dict[tuple[str, str | None], list[Decimal]] = {}
        unidade = ""
        datas: list[str] = []
        leitor = csv.DictReader(io.StringIO(texto.lstrip("﻿")), delimiter=";")
        for linha in leitor:
            if limpa_texto(linha.get("Produto")) != produto:
                continue
            estado = normaliza_uf(linha.get("Estado - Sigla"))
            if estado is None:
                continue
            if uf and estado != uf:
                continue
            valor = valor_br(linha.get("Valor de Venda"))
            if valor is None:
                continue
            chave = (estado, None) if por == "estado" else (limpa_texto(linha.get("Municipio")), estado)
            grupos.setdefault(chave, []).append(valor)
            unidade = unidade or limpa_texto(linha.get("Unidade de Medida"))
            data = limpa_texto(linha.get("Data da Coleta"))
            if data:
                datas.append(data)

        if not grupos and not datas:
            # nem uma linha do produto: ou o arquivo mudou de cara, ou veio vazio
            if not texto.startswith("Regiao") and "Estado - Sigla" not in texto[:300]:
                raise ErroUpstream(self.name)

        itens = []
        for (local, uf_grupo), valores in grupos.items():
            media = sum(valores) / len(valores)
            itens.append(
                PrecoCombustivel(
                    combustivel=combustivel,
                    produto=produto,
                    nivel=por,
                    local=local,
                    uf=uf_grupo if por == "municipio" else local,
                    preco_medio=media.quantize(Decimal("0.01")),
                    preco_minimo=min(valores),
                    preco_maximo=max(valores),
                    coletas=len(valores),
                    unidade=unidade,
                ).model_dump(mode="json")
            )
        # mais barato primeiro, a pergunta é sempre "onde tá mais em conta?"
        itens.sort(key=lambda i: Decimal(i["preco_medio"]))
        itens = itens[: int(limit)]

        datas_ord = sorted(datas, key=lambda d: d.split("/")[::-1])
        meta: dict = {
            "combustivel": combustivel,
            "por": por,
            "coletas_total": sum(len(v) for v in grupos.values()),
            "fonte": FONTE,
        }
        if datas_ord:
            meta["coletas_de"] = datas_ord[0]
            meta["coletas_ate"] = datas_ord[-1]
        if uf:
            meta["uf"] = uf
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=itens, total=len(itens), meta=meta
        )
