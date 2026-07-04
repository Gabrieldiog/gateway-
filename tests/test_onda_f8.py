"""Onda F8 — Brasil no Mundo: os indicadores do Banco Mundial."""


async def test_comparar_ordena_e_descarta_pais_sem_medicao(api):
    resp = await api.get("/v1/mundo/comparar?indicador=expectativa-vida&paises=brasil,argentina,chile,venezuela")
    assert resp.status_code == 200
    corpo = resp.json()
    # Venezuela veio value=null e cai fora; o resto ordenado do maior pro menor
    assert [i["iso3"] for i in corpo["dados"]] == ["CHL", "ARG", "BRA"]
    assert corpo["dados"][0]["valor"] == 81.359
    assert corpo["dados"][0]["ano"] == 2024
    assert corpo["dados"][0]["unidade"] == "anos"


async def test_bom_utf8_na_resposta_nao_quebra(api):
    # a fixture da expectativa é servida com BOM na frente do JSON, como a
    # fonte real faz — o parse tolera
    resp = await api.get("/v1/mundo/serie?indicador=expectativa-vida&pais=chile&ultimos=5")
    assert resp.status_code == 200
    assert resp.json()["total"] == 3


async def test_serie_vem_em_ordem_cronologica(api):
    resp = await api.get("/v1/mundo/serie?indicador=pib-per-capita&ultimos=5")
    anos = [i["ano"] for i in resp.json()["dados"]]
    assert anos == [2023, 2024, 2025]


async def test_painel_junta_os_oito_indicadores(api):
    resp = await api.get("/v1/mundo/painel")
    corpo = resp.json()
    assert corpo["meta"]["pedidos"] == 8
    assert corpo["total"] >= 8  # cada indicador respondeu ao menos o Brasil
    rotulos = {i["indicador"] for i in corpo["dados"]}
    assert "Expectativa de vida" in rotulos


async def test_indicador_desconhecido_da_400_com_o_cardapio(api):
    resp = await api.get("/v1/mundo/comparar?indicador=felicidade")
    assert resp.status_code == 400
    assert "pib-per-capita" in str(resp.json()["detalhes"])


async def test_codigo_cru_invalido_vira_400_nao_500(api):
    # código com cara de código, mas que o Banco Mundial não conhece
    resp = await api.get("/v1/mundo/comparar?indicador=XX.BAD")
    assert resp.status_code == 400


async def test_pais_desconhecido_da_400(api):
    resp = await api.get("/v1/mundo/comparar?indicador=gini&paises=brasil,atlantida")
    assert resp.status_code == 400
    assert "argentina" in str(resp.json()["detalhes"])
