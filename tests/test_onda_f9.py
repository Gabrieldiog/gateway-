"""Onda F9, Desmatamento: os alertas DETER agregados."""


async def test_agrega_por_uf_e_ordena_por_area(api):
    resp = await api.get("/v1/inpe/desmatamento?dias=30")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["meta"]["alertas_total"] == 6
    assert corpo["meta"]["area_total_km2"] == 39.0
    assert corpo["meta"]["ultima_deteccao"] == "2026-06-26"
    # MT soma 22 km² em 3 alertas e lidera
    mt = corpo["dados"][0]
    assert mt["nome"] == "MT"
    assert mt["alertas"] == 3
    assert mt["area_km2"] == 22.0


async def test_agrega_por_classe_com_nome_legivel(api):
    resp = await api.get("/v1/inpe/desmatamento?por=classe")
    classes = {i["nome"]: i for i in resp.json()["dados"]}
    # DESMATAMENTO_CR virou "corte raso"; MINERACAO virou "mineração"
    assert classes["corte raso"]["alertas"] == 3
    assert classes["mineração"]["area_km2"] == 3.0


async def test_agrega_por_municipio_com_uf(api):
    resp = await api.get("/v1/inpe/desmatamento?por=municipio&limit=2")
    itens = resp.json()["dados"]
    assert itens[0]["nome"] == "Colniza (MT)"  # 12,5 + 2,0 km²
    assert itens[0]["area_km2"] == 14.5
    assert len(itens) == 2


async def test_cerrado_usa_a_outra_camada(api):
    resp = await api.get("/v1/inpe/desmatamento?bioma=cerrado&por=municipio")
    corpo = resp.json()
    assert corpo["meta"]["alertas_total"] == 2
    assert corpo["dados"][0]["nome"] == "Baixa Grande Do Ribeiro (PI)"


async def test_parametros_invalidos_dao_400(api):
    assert (await api.get("/v1/inpe/desmatamento?bioma=pampa")).status_code == 400
    assert (await api.get("/v1/inpe/desmatamento?dias=365")).status_code == 400
    assert (await api.get("/v1/inpe/desmatamento?por=fazenda")).status_code == 400
