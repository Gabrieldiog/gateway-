"""Onda F2, Querido Diário: busca nos diários oficiais municipais."""


async def test_busca_no_diario_oficial(api):
    resp = await api.get("/v1/diarios/busca?municipio=5208707&q=dispensa de licitação")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["meta"]["total_diarios"] == 2687
    assert corpo["meta"]["tem_proxima"] is True
    d = corpo["dados"][0]
    assert d["municipio"] == "Goiânia"
    assert d["uf"] == "GO"
    assert d["data"] == "2026-07-02"
    assert d["edicao"] == "8811"
    assert "DISPENSA" in d["trechos"][0]
    assert d["url"].endswith(".pdf")
    # a edição extra vem marcada
    assert corpo["dados"][1]["extra"] is True


async def test_busca_exige_termo(api):
    resp = await api.get("/v1/diarios/busca?municipio=5208707")
    assert resp.status_code == 400


async def test_cobertura_por_nome(api):
    resp = await api.get("/v1/diarios/cobertura?nome=goi")
    corpo = resp.json()
    assert corpo["dados"][0]["nome"] == "Goiânia"
    assert corpo["dados"][0]["ibge"] == 5208707


async def test_diarios_aparece_em_fontes(api):
    resp = await api.get("/v1/fontes")
    nomes = {f["nome"] for f in resp.json()["fontes"]}
    assert "diarios" in nomes
