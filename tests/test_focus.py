async def test_focus_expectativa_por_indicador(api):
    resp = await api.get("/v1/focus/ipca?ano=2026")
    assert resp.status_code == 200
    ind = resp.json()["dados"][0]
    assert ind["indicador"] == "IPCA"
    assert ind["referencia"] == "2026"
    assert ind["mediana"] == 5.33
    assert ind["unidade"] == "%"
    assert ind["respondentes"] == 148


async def test_focus_cambio_vem_em_reais(api):
    resp = await api.get("/v1/focus/cambio?ano=2026")
    ind = resp.json()["dados"][0]
    assert ind["indicador"] == "Câmbio"
    assert ind["unidade"] == "R$"


async def test_focus_painel_junta_os_indicadores(api):
    resp = await api.get("/v1/focus/painel?ano=2026")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["meta"]["painel"] == "expectativas do mercado"
    indicadores = {d["indicador"] for d in corpo["dados"]}
    assert {"IPCA", "Selic", "Câmbio", "PIB Total", "IGP-M"} <= indicadores


async def test_focus_ano_invalido_da_400(api):
    resp = await api.get("/v1/focus/ipca?ano=abc")
    assert resp.status_code == 400


async def test_focus_indicador_desconhecido_da_404(api):
    resp = await api.get("/v1/focus/bitcoin")
    assert resp.status_code == 404
