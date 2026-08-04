"""Onda F1, Minha Cidade: Censo 2022 e PIB municipal."""


async def test_censo_da_cidade_junta_as_duas_tabelas(api):
    resp = await api.get("/v1/sidra/censo?municipio=3550308")
    assert resp.status_code == 200
    c = resp.json()["dados"][0]
    assert c["municipio"] == "São Paulo (SP)"
    assert c["populacao"] == 11451999
    assert c["crescimento_aa_pct"] == 0.15
    assert c["domicilios"] == 4307665
    assert c["moradores_por_domicilio"] == 2.65
    assert c["ano"] == 2022


async def test_pib_municipal_em_reais(api):
    resp = await api.get("/v1/sidra/pib?municipio=3550308")
    assert resp.status_code == 200
    p = resp.json()["dados"][0]
    # a fonte fala em mil reais; entregamos reais
    assert p["pib"] == "1066825105000"
    assert p["ano"] == 2023


async def test_censo_exige_municipio_de_7_digitos(api):
    resp = await api.get("/v1/sidra/censo?municipio=355030")
    assert resp.status_code == 400
