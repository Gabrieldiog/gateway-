"""Os CSVs diários do SICONV/Transferegov que ligam a obra ao dinheiro de
verdade — as duas pontas que a API do Obrasgov não entrega:

- siconv_empenho_cipi.csv.zip (~1MB): a nota de empenho de cada obra (UG +
  número), que abre a porta do detalhe no Portal da Transparência.
- siconv_contrato_cipi.csv.zip (~3,5MB): o contrato que o município assinou —
  a EMPREITEIRA final, com CNPJ, valor e modalidade de licitação.

Os dois são keyed por ID_PROJETO_INVESTIMENTO (o idUnico do Obrasgov). O
repositório atualiza toda manhã, então o índice em memória vence em 24h.
Formato: UTF-8 com BOM, ponto e vírgula, vírgula decimal e datas ora
dd/mm/aaaa ora ISO — tudo normalizado aqui."""

import asyncio
import csv
import io
import time
import zipfile
import zlib

import httpx

from balcao.exceptions import ErroUpstream
from balcao.normalize import limpa_texto, para_data, valor_br

ARQUIVOS = {
    "empenhos": "siconv_empenho_cipi.csv.zip",
    "contratos": "siconv_contrato_cipi.csv.zip",
}


def _monta_empenhos(dado: bytes) -> dict[str, list[dict]]:
    por_obra: dict[str, list[dict]] = {}
    for linha in _linhas(dado):
        id_obra = (linha.get("ID_PROJETO_INVESTIMENTO") or "").strip()
        if not id_obra:
            continue
        valor = valor_br(linha.get("VALOR_EMPENHO"))
        por_obra.setdefault(id_obra, []).append(
            {
                "ug": (linha.get("UG_EMITENTE") or "").strip() or None,
                "nota": (linha.get("NR_EMPENHO") or "").strip() or None,
                "valor": str(valor) if valor is not None else None,
                "natureza": (linha.get("NATUREZA_DESPESA") or "").strip() or None,
                "data": (d.isoformat() if (d := para_data(linha.get("DATA_EMISSAO"))) else None),
            }
        )
    return por_obra


def _monta_contratos(dado: bytes) -> dict[str, list[dict]]:
    por_obra: dict[str, list[dict]] = {}
    for linha in _linhas(dado):
        id_obra = (linha.get("ID_PROJETO_INVESTIMENTO") or "").strip()
        if not id_obra:
            continue
        valor = valor_br(linha.get("VALOR_GLOBAL_CONTRATO"))
        por_obra.setdefault(id_obra, []).append(
            {
                "numero": limpa_texto(linha.get("NR_CONTRATO")) or None,
                "fornecedor": limpa_texto(linha.get("NOME_FORNECEDOR_CONTRATO")) or None,
                "cnpj": (linha.get("ID_FORNECEDOR_CONTRATO") or "").strip() or None,
                "valor": str(valor) if valor is not None else None,
                "objeto": limpa_texto(linha.get("OBJETO_CONTRATO")) or None,
                "modalidade_licitacao": limpa_texto(linha.get("MODALIDADE_LICITACAO")) or None,
                "licitacao": limpa_texto(linha.get("NR_LICITACAO")) or None,
                "situacao": limpa_texto(linha.get("SITUACAO")) or None,
                "orgao": limpa_texto(linha.get("DESC_ORGAO")) or None,
                "assinatura": (d.isoformat() if (d := para_data(linha.get("DATA_ASSINATURA_CONTRATO"))) else None),
                "fim_vigencia": (d.isoformat() if (d := para_data(linha.get("DATA_FIM_VIGENCIA_CONTRATO"))) else None),
            }
        )
    return por_obra


def _linhas(dado: bytes):
    with zipfile.ZipFile(io.BytesIO(dado)) as z:
        with z.open(z.namelist()[0]) as arquivo:
            texto = io.TextIOWrapper(arquivo, encoding="utf-8-sig", newline="")
            yield from csv.DictReader(texto, delimiter=";")


MONTADORES = {"empenhos": _monta_empenhos, "contratos": _monta_contratos}


class ArquivosSiconv:
    BASE = "https://repositorio.dados.gov.br/seges/detru"
    FRESCOR = 24 * 3600.0  # o repositório republica os CSVs toda manhã
    ESPERA_POS_FALHA = 60.0  # com a fonte fora, não martela de novo já

    def __init__(self, client: httpx.AsyncClient, relogio=time.monotonic):
        self.client = client
        self._relogio = relogio
        self._cache: dict[str, tuple[dict[str, list[dict]], float]] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._falha_em: dict[str, float] = {}

    async def empenhos(self, id_obra: str) -> list[dict]:
        return (await self._indice("empenhos")).get(id_obra, [])

    async def contratos(self, id_obra: str) -> list[dict]:
        return (await self._indice("contratos")).get(id_obra, [])

    async def _indice(self, nome: str) -> dict[str, list[dict]]:
        guardado = self._cache.get(nome)
        if guardado and self._relogio() - guardado[1] < self.FRESCOR:
            return guardado[0]
        lock = self._locks.setdefault(nome, asyncio.Lock())
        async with lock:
            guardado = self._cache.get(nome)
            if guardado and self._relogio() - guardado[1] < self.FRESCOR:
                return guardado[0]
            # a fonte acabou de falhar: quem chega em seguida não repete o
            # download de 120s — serve o índice de ontem ou o erro limpo
            falhou_em = self._falha_em.get(nome)
            if falhou_em is not None and self._relogio() - falhou_em < self.ESPERA_POS_FALHA:
                if guardado:
                    return guardado[0]
                raise ErroUpstream("siconv")
            try:
                resp = await self.client.get(
                    f"{self.BASE}/{ARQUIVOS[nome]}", timeout=httpx.Timeout(120.0)
                )
                resp.raise_for_status()
                indice = await asyncio.to_thread(MONTADORES[nome], resp.content)
            except httpx.HTTPStatusError as exc:
                self._falha_em[nome] = self._relogio()
                if guardado:
                    return guardado[0]  # vencido, mas é o dado de ontem — serve
                raise ErroUpstream("siconv", exc.response.status_code) from exc
            except (
                httpx.HTTPError,
                zipfile.BadZipFile,
                zlib.error,
                csv.Error,
                UnicodeDecodeError,
                IndexError,  # zip 200 porém sem membro nenhum
            ) as exc:
                self._falha_em[nome] = self._relogio()
                if guardado:
                    return guardado[0]
                raise ErroUpstream("siconv") from exc
            self._falha_em.pop(nome, None)
            self._cache[nome] = (indice, self._relogio())
            return indice
