async def test_alertas_normalizados(api):
    resp = await api.get("/v1/infodengue/alertas?municipio=5208707")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["meta"]["fonte"]["nome"].startswith("InfoDengue")
    assert corpo["meta"]["doenca"] == "dengue"
    atual = corpo["dados"][0]
    assert atual["municipio"] == "Goiânia"
    assert atual["semana"] == 202624
    assert atual["nivel"] == 4
    assert atual["alerta"] == "vermelho"
    assert atual["casos"] == 341
    assert atual["casos_estimados"] == 1607.5
    # epoch em ms vira data ISO do início da semana
    assert atual["inicio_semana"] == "2026-06-14"


async def test_alertas_niveis_por_extenso(api):
    resp = await api.get("/v1/infodengue/alertas?municipio=5208707&doenca=dengue")
    dados = resp.json()["dados"]
    verde = next(d for d in dados if d["nivel"] == 1)
    assert verde["alerta"] == "verde"


async def test_municipio_invalido_da_400(api):
    resp = await api.get("/v1/infodengue/alertas?municipio=123")
    assert resp.status_code == 400


async def test_doenca_invalida_da_400(api):
    resp = await api.get("/v1/infodengue/alertas?municipio=5208707&doenca=gripe")
    assert resp.status_code == 400
    assert "chikungunya" in resp.json()["detalhes"]["parametros_aceitos"]
