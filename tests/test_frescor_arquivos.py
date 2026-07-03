"""Certificação de frescor dos dois conectores file-backed: ano fechado é
história (cache eterno), ano corrente revalida sozinho."""

import asyncio
import os
import time
from datetime import date
from pathlib import Path

import httpx
from httpx import MockTransport

from balcao.arquivos import ArquivoVotos, IndiceAno
from balcao.connectors.tse import TseConnector

ANO_ATUAL = date.today().year


async def test_indice_do_ano_corrente_vence_e_remonta():
    relogio = {"agora": 0.0}
    montagens = {"n": 0}

    arquivo = ArquivoVotos(client=None, relogio=lambda: relogio["agora"])

    async def monta_fake(ano):
        montagens["n"] += 1
        return IndiceAno(ano=ano, por_deputado={}, por_votacao={})

    arquivo._baixa_e_monta = monta_fake

    await arquivo.indice(ANO_ATUAL)
    await arquivo.indice(ANO_ATUAL)
    assert montagens["n"] == 1  # dentro da validade: cache

    relogio["agora"] = 7 * 3600.0  # passou das 6h de validade
    await arquivo.indice(ANO_ATUAL)
    assert montagens["n"] == 2  # remontou sozinho


async def test_indice_de_ano_fechado_nunca_vence():
    relogio = {"agora": 0.0}
    montagens = {"n": 0}
    arquivo = ArquivoVotos(client=None, relogio=lambda: relogio["agora"])

    async def monta_fake(ano):
        montagens["n"] += 1
        return IndiceAno(ano=ano, por_deputado={}, por_votacao={})

    arquivo._baixa_e_monta = monta_fake

    await arquivo.indice(ANO_ATUAL - 2)
    relogio["agora"] = 365 * 24 * 3600.0  # um ano depois
    await arquivo.indice(ANO_ATUAL - 2)
    assert montagens["n"] == 1  # história não vence


async def test_zip_do_tse_revalida_so_na_eleicao_corrente(tmp_path: Path):
    downloads = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        downloads["n"] += 1
        return httpx.Response(200, content=b"PK\x05\x06" + b"\x00" * 18)  # zip vazio válido

    cliente = httpx.AsyncClient(transport=MockTransport(handler))
    conector = TseConnector(cliente)
    conector.pasta = tmp_path

    # eleição fechada com arquivo velho: não baixa de novo
    antigo = tmp_path / "prestacao-2022.zip"
    antigo.write_bytes(b"PK\x05\x06" + b"\x00" * 18)
    os.utime(antigo, (time.time() - 40 * 24 * 3600,) * 2)
    await conector._garante_zip(2022)
    assert downloads["n"] == 0

    # eleição do ano corrente com arquivo de 40 dias: revalida (baixa de novo)
    corrente = tmp_path / f"prestacao-{ANO_ATUAL}.zip"
    corrente.write_bytes(b"PK\x05\x06" + b"\x00" * 18)
    os.utime(corrente, (time.time() - 40 * 24 * 3600,) * 2)
    await conector._garante_zip(ANO_ATUAL)
    assert downloads["n"] == 1

    # e recém-baixado, não baixa de novo
    await conector._garante_zip(ANO_ATUAL)
    assert downloads["n"] == 1
    await cliente.aclose()
