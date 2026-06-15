async def test_series_busca(api):
    resp = await api.get("/v1/ipeadata/series?q=IPCA&limite=2")
    assert resp.status_code == 200
    corpo = resp.json()
    s = corpo["dados"][0]
    assert s["codigo"] == "BM12_IPCA2012"
    assert s["periodicidade"] == "Mensal"
    assert s["fonte_dados"] == "Banco Central do Brasil"
    assert s["ativa"] is True
    # a segunda série tem SERSTATUS = "I" (inativa/descontinuada)
    assert corpo["dados"][1]["ativa"] is False


async def test_valores_recorta_recentes(api):
    resp = await api.get("/v1/ipeadata/serie/BM12_IPCA2012?ultimos=3")
    assert resp.status_code == 200
    corpo = resp.json()
    # a série tem 5 pontos; o conector recorta os 3 últimos (a fonte manda tudo)
    assert corpo["meta"]["total_serie"] == 5
    assert corpo["total"] == 3
    datas = [p["data"] for p in corpo["dados"]]
    assert datas == ["2026-03-01", "2026-04-01", "2026-05-01"]
    assert corpo["dados"][0]["valor"] == 0.41
    # VALVALOR null vira None sem derrubar o ponto
    assert corpo["dados"][-1]["valor"] is None


async def test_param_invalido_da_400(api):
    resp = await api.get("/v1/ipeadata/series?tema=1")
    assert resp.status_code == 400


async def test_ipeadata_aparece_em_fontes(api):
    resp = await api.get("/v1/fontes")
    nomes = {f["nome"] for f in resp.json()["fontes"]}
    assert "ipeadata" in nomes
