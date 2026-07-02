import httpx
import pytest
from httpx import MockTransport

from balcao.connectors.b3 import B3Connector
from balcao.exceptions import ChaveFaltando


async def test_acoes_fan_out_e_normaliza(api):
    resp = await api.get("/v1/b3/acoes/ibov,PETR4")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["meta"]["fonte"]["nome"].startswith("B3")
    assert "atraso" in corpo["meta"]
    ibov = next(a for a in corpo["dados"] if a["ticker"] == "IBOV")
    # o apelido ibov vira ^BVSP na fonte e volta como IBOV, em pontos (sem moeda)
    assert float(ibov["preco"]) == 171688.61
    assert ibov["nome"] == "Ibovespa"
    assert ibov["moeda"] is None
    petr = next(a for a in corpo["dados"] if a["ticker"] == "PETR4")
    assert float(petr["preco"]) == 37.83
    assert petr["moeda"] == "BRL"


async def test_acoes_limite_de_tickers(api):
    resp = await api.get("/v1/b3/acoes/A1,B2,C3,D4,E5,F6")
    assert resp.status_code == 400


async def test_b3_e_cacheavel(api):
    primeira = await api.get("/v1/b3/acoes/VALE3")
    assert "cache" not in primeira.json()["meta"]
    segunda = await api.get("/v1/b3/acoes/VALE3")
    # dado com atraso de 15 min pode (e deve) ser cacheado
    assert segunda.json()["meta"]["cache"] == "hit"


async def test_sem_token_da_erro_limpo():
    cliente = httpx.AsyncClient(
        transport=MockTransport(lambda r: httpx.Response(200, json={}))
    )
    conector = B3Connector(cliente, token="")
    with pytest.raises(ChaveFaltando) as exc:
        await conector.fetch("acoes/PETR4")
    assert "BRAPI_TOKEN" in exc.value.mensagem
    await cliente.aclose()
