async def test_bacen_selic_por_apelido(api):
    resp = await api.get("/v1/bacen/selic?ultimos=5")
    assert resp.status_code == 200
    corpo = resp.json()
    ponto = corpo["dados"][0]
    assert ponto["serie"] == 432
    assert ponto["nome"] == "selic"
    # a fonte manda dd/mm/aaaa e o gateway entrega ISO
    assert ponto["data"] is None or ponto["data"][4] == "-"


async def test_bacen_serie_por_codigo_equivale_ao_apelido(api):
    por_codigo = (await api.get("/v1/bacen/serie/432?ultimos=5")).json()
    por_apelido = (await api.get("/v1/bacen/selic?ultimos=5")).json()
    assert [p["valor"] for p in por_codigo["dados"]] == [
        p["valor"] for p in por_apelido["dados"]
    ]


async def test_bacen_ultimos_invalido_da_400(api):
    resp = await api.get("/v1/bacen/selic?ultimos=muitos")
    assert resp.status_code == 400


async def test_ibge_estados(api):
    resp = await api.get("/v1/ibge/estados")
    assert resp.status_code == 200
    estado = resp.json()["dados"][0]
    assert set(estado) >= {"id", "sigla", "nome", "regiao"}


async def test_ibge_municipios_desaninha_uf(api):
    resp = await api.get("/v1/ibge/municipios?uf=SP")
    assert resp.status_code == 200
    municipio = resp.json()["dados"][0]
    # na fonte a UF mora tres niveis abaixo; aqui sai plana
    assert municipio["uf"] == "SP"
    assert municipio["regiao"] == "Sudeste"


async def test_senado_senadores_normalizados(api):
    resp = await api.get("/v1/senado/senadores")
    assert resp.status_code == 200
    senador = resp.json()["dados"][0]
    assert set(senador) >= {"id", "nome", "partido", "uf"}
    assert isinstance(senador["id"], int)


async def test_senado_filtra_por_uf_no_gateway(api):
    todos = (await api.get("/v1/senado/senadores")).json()
    ufs = {s["uf"] for s in todos["dados"]}
    alvo = next(iter(ufs))
    filtrados = (await api.get(f"/v1/senado/senadores?uf={alvo}")).json()
    assert filtrados["total"] >= 1
    assert all(s["uf"] == alvo for s in filtrados["dados"])
