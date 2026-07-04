"""Resiliência dos CSVs do SICONV: fonte fora serve o índice de ontem,
parse quebrado vira erro limpo, e falha recente não vira martelo."""

import zipfile
from pathlib import Path

import httpx
import pytest
from httpx import MockTransport

from balcao.exceptions import ErroUpstream
from balcao.siconv import ArquivosSiconv

FIXTURES = Path(__file__).parent / "fixtures"


class Relogio:
    def __init__(self):
        self.agora = 1000.0

    def __call__(self):
        return self.agora


def cliente_que(responde):
    return httpx.AsyncClient(transport=MockTransport(responde))


async def test_fonte_fora_serve_o_indice_de_ontem():
    zip_bom = (FIXTURES / "siconv_empenho.zip").read_bytes()
    chamadas = {"n": 0}

    def responde(request):
        chamadas["n"] += 1
        if chamadas["n"] == 1:
            return httpx.Response(200, content=zip_bom)
        return httpx.Response(503)

    relogio = Relogio()
    siconv = ArquivosSiconv(cliente_que(responde), relogio=relogio)
    assert await siconv.empenhos("11370.52-41")  # monta o índice

    relogio.agora += 25 * 3600  # venceu o frescor de 24h
    # o refresh falha (503), mas o dado de ontem continua servindo
    assert await siconv.empenhos("11370.52-41")
    assert chamadas["n"] == 2


async def test_falha_recente_nao_vira_martelo():
    chamadas = {"n": 0}

    def responde(request):
        chamadas["n"] += 1
        return httpx.Response(503)

    relogio = Relogio()
    siconv = ArquivosSiconv(cliente_que(responde), relogio=relogio)
    with pytest.raises(ErroUpstream):
        await siconv.empenhos("11370.52-41")
    # nova chamada logo em seguida: erro limpo SEM novo download
    with pytest.raises(ErroUpstream):
        await siconv.empenhos("11370.52-41")
    assert chamadas["n"] == 1

    relogio.agora += 120  # passada a espera, tenta a fonte de novo
    with pytest.raises(ErroUpstream):
        await siconv.empenhos("11370.52-41")
    assert chamadas["n"] == 2


async def test_zip_vazio_ou_corrompido_vira_erro_upstream(tmp_path):
    vazio = tmp_path / "vazio.zip"
    with zipfile.ZipFile(vazio, "w"):
        pass  # zip válido, mas sem nenhum membro

    for corpo in (vazio.read_bytes(), b"isto nao e um zip"):
        siconv = ArquivosSiconv(
            cliente_que(lambda req, c=corpo: httpx.Response(200, content=c)),
            relogio=Relogio(),
        )
        with pytest.raises(ErroUpstream):
            await siconv.empenhos("11370.52-41")
