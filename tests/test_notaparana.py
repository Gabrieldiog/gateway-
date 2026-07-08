from decimal import Decimal

import httpx
from httpx import MockTransport

from balcao.connectors.notaparana import NotaParanaConnector


async def test_produtos_normalizados(api):
    resp = await api.get("/v1/notaparana/produtos?termo=dipirona&lat=-25.4284&lon=-49.2733")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["meta"]["fonte"]["nome"].startswith("Nota Paraná")
    assert corpo["meta"]["termo"] == "dipirona"
    p = corpo["dados"][0]
    assert p["descricao"] == "DIPIRONA SOD CAF E"
    assert p["gtin"] == "7896714273198"
    assert p["estabelecimento"] == "FARMACIAS PAGUE MENOS"
    assert p["municipio"] == "CURITIBA"
    assert p["uf"] == "PR"
    assert "MUNHOZ DA ROCHA" in p["endereco"]


async def test_valor_us_nao_vira_br(api):
    # a fonte manda "1.04" (formato US); tem que virar R$1,04, não 104
    resp = await api.get("/v1/notaparana/produtos?termo=dipirona&lat=-25.4&lon=-49.2")
    p = resp.json()["dados"][0]
    assert p["valor"] == "1.04"
    assert Decimal(p["valor"]) < Decimal("2")


async def test_aceita_local_junto(api):
    resp = await api.get("/v1/notaparana/produtos?termo=dipirona&local=-25.4,-49.2")
    assert resp.status_code == 200
    assert resp.json()["meta"]["local"] == "-25.4,-49.2"


async def test_sem_termo_da_400(api):
    resp = await api.get("/v1/notaparana/produtos?lat=-25.4&lon=-49.2")
    assert resp.status_code == 400


async def test_sem_local_da_400(api):
    resp = await api.get("/v1/notaparana/produtos?termo=dipirona")
    assert resp.status_code == 400
    assert "lat" in str(resp.json()["detalhes"])


async def test_recurso_invalido_da_404(api):
    resp = await api.get("/v1/notaparana/inexistente")
    assert resp.status_code == 404


async def test_total_conta_itens_nao_o_da_fonte():
    # a fonte diz total=99 (é o total da paginação), mas só 1 produto tem preço.
    # o envelope tem que anunciar total=1 (o que de fato veio) e guardar 99 no meta.
    # de quebra: gtin/ncm inteiros têm que virar string, não estourar o Pydantic.
    payload = {
        "total": 99,
        "produtos": [
            {"desc": "DIPIRONA", "valor": "1.04", "gtin": 123, "ncm": 456,
             "estabelecimento": {"nm_fan": "X", "mun": "CURITIBA", "uf": "PR"}},
            {"desc": "SEM PRECO", "valor": None,
             "estabelecimento": {"nm_fan": "Y", "mun": "CURITIBA", "uf": "PR"}},
        ],
    }

    async with httpx.AsyncClient(transport=MockTransport(lambda req: httpx.Response(200, json=payload))) as c:
        r = await NotaParanaConnector(c).fetch("produtos", termo="dipirona", local="-25.4,-49.2")

    assert r.total == 1
    assert len(r.dados) == 1
    assert r.meta["total_fonte"] == 99
    assert r.dados[0]["gtin"] == "123"
    assert r.dados[0]["ncm"] == "456"
