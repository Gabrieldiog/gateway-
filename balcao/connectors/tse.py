"""TSE: doações de campanha, da prestação de contas eleitoral. O modo mais
duro de fonte que existe, não é API, é um ZIP de centenas de MB (2022) a
1,4 GB (2024) com 112 CSVs dentro, latin-1, ponto e vírgula e vírgula
decimal. O conector baixa o ZIP UMA vez pro disco (streaming, sem estourar
memória), lê só o CSV da UF pedida direto de dentro do arquivo e agrega as
doações por candidato, partido, doador ou origem."""

import asyncio
import csv
import io
import os
import tempfile
import time
import zipfile
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx

from balcao.connectors.base import BaseConnector, NormalizedResponse, register
from balcao.exceptions import ErroUpstream, ParametroInvalido, RecursoNaoEncontrado
from balcao.models import DoacaoAgregada
from balcao.normalize import UFS, limpa_texto, valor_br


def anos_de_eleicao() -> set[int]:
    """Eleicao a cada dois anos desde 2022. O ano corrente ja entra na lista:
    quando o TSE publicar o arquivo da eleicao nova, funciona sem mexer em
    codigo, ate la, o download responde erro limpo de nao publicado."""
    return {a for a in range(2022, date.today().year + 1) if a % 2 == 0}
NIVEIS = {"candidato", "partido", "doador", "origem"}

PARAMS = {"ano", "uf", "por", "limit"}

FONTE = {
    "nome": "TSE, Prestação de Contas Eleitorais",
    "url": "https://dadosabertos.tse.jus.br",
    "nota": (
        "Receitas declaradas pelos próprios candidatos ao TSE. CPF de doador "
        "pessoa física pode vir mascarado (LGPD); CNPJ vem completo. O arquivo "
        "do ano é baixado uma única vez e fica em cache no disco."
    ),
}


@register
class TseConnector(BaseConnector):
    name = "tse"
    base_url = "https://cdn.tse.jus.br/estatistica/sead/odsele/prestacao_contas"
    description = "TSE: doações de campanha por candidato, partido, doador e origem (2022 e 2024)"
    resources = {
        "doacoes": (
            "doações agregadas de uma UF (params: uf obrigatória; ano = 2022|2024; "
            "por = candidato|partido|doador|origem; limit). A 1ª consulta de um ano "
            "baixa um arquivo grande (minutos), depois fica em cache no disco"
        ),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pasta = Path(tempfile.gettempdir()) / "balcao-tse"
        self._locks: dict[int, asyncio.Lock] = {}

    async def fetch(self, recurso: str, **params: Any) -> NormalizedResponse:
        partes = [p for p in recurso.strip("/").split("/") if p]
        match partes:
            case ["doacoes"]:
                return await self._doacoes(recurso, params)
            case _:
                raise RecursoNaoEncontrado(self.name, recurso, sorted(self.resources))

    async def _doacoes(self, recurso: str, params: dict) -> NormalizedResponse:
        invalidos = sorted(set(params) - PARAMS)
        if invalidos:
            raise ParametroInvalido(recurso, invalidos, sorted(PARAMS))
        uf = str(params.get("uf", "")).strip().upper()
        if uf not in UFS:
            raise ParametroInvalido(recurso, ["uf"], ["sigla de UF (obrigatória)"])
        # padrao: a ultima eleicao ja consolidada (a prestacao fecha no ano
        # seguinte ao pleito); a eleicao do ano corrente pode ser pedida
        # explicitamente assim que o TSE publicar
        anos = anos_de_eleicao()
        consolidadas = [a for a in anos if a < date.today().year] or [2022]
        ano = params.get("ano", max(consolidadas))
        if not str(ano).isdigit() or int(ano) not in anos:
            raise ParametroInvalido(recurso, ["ano"], sorted(str(a) for a in anos))
        ano = int(ano)
        por = str(params.get("por", "candidato")).lower()
        if por not in NIVEIS:
            raise ParametroInvalido(recurso, ["por"], sorted(NIVEIS))
        limit = params.get("limit", 20)
        if not str(limit).isdigit() or not (1 <= int(limit) <= 100):
            raise ParametroInvalido(recurso, ["limit"], ["1..100"])

        caminho = await self._garante_zip(ano)
        # parse de dezenas de MB é trabalho de CPU/disco, sai do event loop
        grupos, total_doacoes = await asyncio.to_thread(self._agrega, caminho, ano, uf, por)

        itens = [
            DoacaoAgregada(
                ano=ano, uf=uf, nivel=por, nome=nome, detalhe=detalhe or None,
                total=total.quantize(Decimal("0.01")), doacoes=qtd,
            ).model_dump(mode="json")
            for (nome, detalhe), (total, qtd) in grupos.items()
        ]
        itens.sort(key=lambda i: Decimal(i["total"]), reverse=True)
        itens = itens[: int(limit)]

        meta = {"ano": ano, "uf": uf, "por": por, "doacoes_total": total_doacoes, "fonte": FONTE}
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=itens, total=len(itens), meta=meta
        )

    def _zip_fresco(self, caminho: Path, ano: int) -> bool:
        """Eleicao consolidada e imutavel: o ZIP baixado vale pra sempre. A
        eleicao do ano corrente (campanha em andamento, o TSE atualiza o
        arquivo) revalida a cada 24h pelo mtime."""
        if not caminho.exists():
            return False
        if ano < date.today().year:
            return True
        return (time.time() - caminho.stat().st_mtime) < 24 * 3600

    async def _garante_zip(self, ano: int) -> Path:
        """Baixa o ZIP do ano por streaming direto pro disco, uma vez pra
        eleicao fechada, com revalidacao diaria pra eleicao em curso."""
        caminho = self.pasta / f"prestacao-{ano}.zip"
        if self._zip_fresco(caminho, ano):
            return caminho
        lock = self._locks.setdefault(ano, asyncio.Lock())
        async with lock:
            if self._zip_fresco(caminho, ano):
                return caminho
            self.pasta.mkdir(parents=True, exist_ok=True)
            url = f"{self.base_url}/prestacao_de_contas_eleitorais_candidatos_{ano}.zip"
            parcial = caminho.with_suffix(".part")
            try:
                async with self.client.stream("GET", url, timeout=httpx.Timeout(900.0)) as resp:
                    resp.raise_for_status()
                    with open(parcial, "wb") as arq:
                        async for pedaco in resp.aiter_bytes(1 << 20):
                            arq.write(pedaco)
                os.replace(parcial, caminho)  # só vira definitivo se baixou inteiro
            except httpx.HTTPStatusError as exc:
                parcial.unlink(missing_ok=True)
                raise ErroUpstream(self.name, exc.response.status_code) from exc
            except httpx.HTTPError as exc:
                parcial.unlink(missing_ok=True)
                raise ErroUpstream(self.name) from exc
            return caminho

    @staticmethod
    def _agrega(caminho: Path, ano: int, uf: str, por: str):
        membro = f"receitas_candidatos_{ano}_{uf}.csv"
        grupos: dict[tuple[str, str], list] = {}
        total = 0
        try:
            with zipfile.ZipFile(caminho) as z, z.open(membro) as arquivo:
                texto = io.TextIOWrapper(arquivo, encoding="latin-1", newline="")
                for linha in csv.DictReader(texto, delimiter=";"):
                    valor = valor_br(linha.get("VR_RECEITA"))
                    if valor is None:
                        continue
                    if por == "candidato":
                        chave = (
                            limpa_texto(linha.get("NM_CANDIDATO")),
                            " · ".join(
                                x for x in (
                                    limpa_texto(linha.get("SG_PARTIDO")),
                                    limpa_texto(linha.get("DS_CARGO")),
                                ) if x
                            ),
                        )
                    elif por == "partido":
                        chave = (limpa_texto(linha.get("SG_PARTIDO")), "")
                    elif por == "doador":
                        chave = (
                            limpa_texto(linha.get("NM_DOADOR")),
                            limpa_texto(linha.get("NR_CPF_CNPJ_DOADOR")),
                        )
                    else:
                        chave = (limpa_texto(linha.get("DS_ORIGEM_RECEITA")), "")
                    if not chave[0]:
                        continue
                    grupo = grupos.setdefault(chave, [Decimal(0), 0])
                    grupo[0] += valor
                    grupo[1] += 1
                    total += 1
        except (zipfile.BadZipFile, KeyError) as exc:
            # zip corrompido ou UF sem arquivo naquele ano
            raise ErroUpstream("tse") from exc
        return {k: (v[0], v[1]) for k, v in grupos.items()}, total
