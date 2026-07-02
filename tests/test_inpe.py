async def test_inpe_queimadas_por_estado(api):
    resp = await api.get("/v1/inpe/queimadas?por=estado")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["meta"]["total_focos"] == 5
    assert corpo["meta"]["por"] == "estado"
    assert corpo["meta"]["fonte"]["nome"].startswith("INPE")
    top = corpo["dados"][0]
    assert top["nivel"] == "estado"
    assert top["nome"] == "MATO GROSSO"
    assert top["focos"] == 2
    assert top["frp_total"] == 95.9


async def test_inpe_por_bioma_agrega_diferente(api):
    resp = await api.get("/v1/inpe/queimadas?por=bioma")
    dados = resp.json()["dados"]
    cerrado = next(d for d in dados if d["nome"] == "Cerrado")
    assert cerrado["focos"] == 3  # 2 no MT + 1 na BA


async def test_inpe_default_e_por_estado(api):
    resp = await api.get("/v1/inpe/queimadas")
    assert resp.json()["meta"]["por"] == "estado"


async def test_inpe_por_invalido_da_400(api):
    resp = await api.get("/v1/inpe/queimadas?por=galaxia")
    assert resp.status_code == 400


async def test_inpe_data_em_formato_errado_da_400(api):
    resp = await api.get("/v1/inpe/queimadas?data=01-07-2026")
    assert resp.status_code == 400
