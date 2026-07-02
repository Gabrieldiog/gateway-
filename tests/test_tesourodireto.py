async def test_titulos_pega_so_a_data_mais_recente(api):
    resp = await api.get("/v1/tesourodireto/titulos")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["meta"]["fonte"]["nome"].startswith("Tesouro Direto")
    # a fixture mistura 2005, 2015 e 2026 fora de ordem; só 2026-07-01 sai
    assert corpo["meta"]["data"] == "2026-07-01"
    assert corpo["total"] == 3
    assert all(t["data"] == "2026-07-01" for t in corpo["dados"])


async def test_titulos_normaliza_nome_e_valores(api):
    resp = await api.get("/v1/tesourodireto/titulos")
    dados = resp.json()["dados"]
    selic = next(t for t in dados if t["tipo"] == "Tesouro Selic")
    # nome comercial = tipo + ano do vencimento
    assert selic["nome"] == "Tesouro Selic 2029"
    assert selic["vencimento"] == "2029-03-01"
    # "16497,19" com vírgula decimal vira Decimal
    assert float(selic["pu_compra"]) == 16497.19
    assert float(selic["taxa_compra"]) == 0.05
    # ordenado por tipo, depois vencimento
    assert [t["tipo"] for t in dados] == ["Tesouro IPCA+", "Tesouro Prefixado", "Tesouro Selic"]


async def test_titulos_nao_aceita_params(api):
    resp = await api.get("/v1/tesourodireto/titulos?ano=2020")
    assert resp.status_code == 400
