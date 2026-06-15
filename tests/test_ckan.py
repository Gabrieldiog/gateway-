async def test_datasets(api):
    resp = await api.get("/v1/aneel/datasets?limite=2")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["meta"]["total"] == 69
    assert corpo["meta"]["tem_proxima"] is True

    ds = corpo["dados"][0]
    assert ds["fonte"] == "aneel"
    assert ds["titulo"] == "Componentes Tarifárias"
    assert ds["organizacao"] == "ANEEL"
    # o conector marca quais recursos têm datastore (dá pra puxar linha)
    assert any(r["datastore"] for r in ds["recursos"])


async def test_dados_do_datastore(api):
    resp = await api.get("/v1/aneel/dados/res-1?limite=2")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["total"] == 2
    # o "_id" interno do CKAN sai da lista de campos
    assert corpo["meta"]["campos"] == ["agente", "valor"]
    assert corpo["dados"][0]["agente"] == "CEMIG"


async def test_motor_serve_varias_fontes(api):
    # o mesmo motor CKAN responde por MME e ANTT, cada um com seu nome
    for fonte in ("mme", "antt"):
        resp = await api.get(f"/v1/{fonte}/datasets?limite=1")
        assert resp.status_code == 200
        assert resp.json()["dados"][0]["fonte"] == fonte


async def test_recurso_desconhecido_da_404(api):
    resp = await api.get("/v1/aneel/naoexiste")
    assert resp.status_code == 404


async def test_param_invalido_da_400(api):
    resp = await api.get("/v1/aneel/datasets?ordem=desc")
    assert resp.status_code == 400


async def test_fontes_ckan_aparecem(api):
    resp = await api.get("/v1/fontes")
    nomes = {f["nome"] for f in resp.json()["fontes"]}
    assert {"aneel", "mme", "antt"} <= nomes
