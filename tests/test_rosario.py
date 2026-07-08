from decimal import Decimal

import httpx
from httpx import MockTransport

from balcao.connectors.rosario import RosarioConnector


async def test_termo_com_espaco_vai_com_percent20():
    # termo multi-palavra ("dipirona cafeina") nao pode virar "dipirona+cafeina":
    # o httpx poe "+" pra espaco em params, e a VTEX responde 400 pro "+" no ft.
    capturado = {}

    def handler(req):
        capturado["url"] = str(req.url)
        return httpx.Response(200, json=[])

    async with httpx.AsyncClient(transport=MockTransport(handler)) as c:
        await RosarioConnector(c).fetch("produtos", termo="dipirona cafeina")

    assert "ft=dipirona%20cafeina" in capturado["url"].lower()
    assert "+" not in capturado["url"]


async def test_produtos_normalizados(api):
    resp = await api.get("/v1/rosario/produtos?termo=dipirona")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["meta"]["fonte"]["nome"].startswith("Drogaria Rosário")
    assert corpo["meta"]["termo"] == "dipirona"
    p = corpo["dados"][0]
    # o mais barato primeiro (Maxalgina R$3,26 < Dipirona Medley R$17,91)
    assert p["descricao"].startswith("Maxalgina")
    assert p["valor"] == "3.26"
    assert p["gtin"] == "7898133131011"
    assert p["estabelecimento"] == "Drogaria Rosário"
    assert p["municipio"] == "Goiânia"
    assert p["uf"] == "GO"


async def test_preco_em_reais_nao_centavos(api):
    # a VTEX manda o preço em reais (17.91), tem que sair R$17,91 e não 1791
    resp = await api.get("/v1/rosario/produtos?termo=dipirona")
    medley = next(d for d in resp.json()["dados"] if "Medley" in d["descricao"])
    assert medley["valor"] == "17.91"
    assert Decimal(medley["valor"]) < Decimal("100")
    assert medley["valor_tabela"] == "37.2"  # o preço "de"


async def test_fora_de_estoque_e_ignorado(api):
    # o fixture tem 3 produtos, mas um está IsAvailable=false -> só 2 voltam
    resp = await api.get("/v1/rosario/produtos?termo=dipirona")
    corpo = resp.json()
    assert corpo["total"] == 2
    assert len(corpo["dados"]) == 2
    assert all("Fora de Estoque" not in d["descricao"] for d in corpo["dados"])


async def test_sem_termo_da_400(api):
    resp = await api.get("/v1/rosario/produtos")
    assert resp.status_code == 400


async def test_recurso_invalido_da_404(api):
    resp = await api.get("/v1/rosario/inexistente")
    assert resp.status_code == 404
