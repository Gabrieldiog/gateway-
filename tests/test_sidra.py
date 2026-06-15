async def test_producao_por_uf_ordenada(api):
    resp = await api.get("/v1/sidra/producao?produto=soja&ano=2023")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["meta"]["produto"] == "soja"
    assert corpo["meta"]["ano"] == 2023
    assert corpo["meta"]["variavel"] == "quantidade"

    dados = corpo["dados"]
    assert len(dados) == 3
    # maior primeiro: Paraná (38,5 mi t) antes de São Paulo (22 mi t)
    assert dados[0]["localidade"] == "Paraná"
    assert dados[0]["valor"] == 38500000.0
    assert dados[0]["item"] == "Soja (em grão)"
    assert dados[0]["unidade"] == "Toneladas"
    assert dados[0]["localidade_id"] == 41
    # o "-" do SIDRA vira None e cai pro fim
    assert dados[-1]["localidade"] == "Rio Grande do Norte"
    assert dados[-1]["valor"] is None


async def test_rebanho(api):
    resp = await api.get("/v1/sidra/rebanho?animal=bovino")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["meta"]["animal"] == "bovino"
    dados = corpo["dados"]
    assert dados[0]["localidade"] == "Mato Grosso"
    assert dados[0]["variavel"] == "Efetivo dos rebanhos"
    assert dados[0]["unidade"] == "Cabeças"


async def test_produto_invalido_da_400(api):
    resp = await api.get("/v1/sidra/producao?produto=banana")
    assert resp.status_code == 400
    assert "soja" in resp.json()["detalhes"]["parametros_aceitos"]


async def test_municipio_aceito(api):
    resp = await api.get("/v1/sidra/producao?produto=soja&municipio=4106902")
    assert resp.status_code == 200


async def test_param_desconhecido_da_400(api):
    resp = await api.get("/v1/sidra/rebanho?regiao=sul")
    assert resp.status_code == 400


async def test_sidra_aparece_em_fontes(api):
    resp = await api.get("/v1/fontes")
    nomes = {f["nome"] for f in resp.json()["fontes"]}
    assert "sidra" in nomes
