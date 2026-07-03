"""Onda E — agro turbinado: LSPA mensal, abate e leite trimestrais,
municípios campeões e os arquivos diários da CONAB."""


async def test_safra_lspa_junta_as_tres_variaveis(api):
    resp = await api.get("/v1/sidra/safra?produto=soja")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["meta"]["mes"] == "202605"
    s = corpo["dados"][0]
    assert s["localidade"] == "Brasil"
    assert s["producao_t"] == 174587586.0
    assert s["area_plantada_ha"] == 48300000.0
    assert s["rendimento_kg_ha"] == 3617.0


async def test_safra_produto_invalido_da_400(api):
    resp = await api.get("/v1/sidra/safra?produto=banana-da-terra")
    assert resp.status_code == 400
    assert "soja" in resp.json()["detalhes"]["parametros_aceitos"]


async def test_abate_bovino(api):
    resp = await api.get("/v1/sidra/abate?tipo=bovino")
    a = resp.json()["dados"][0]
    assert a["trimestre"] == "1º trimestre 2026"
    assert a["animais"] == 10289201.0
    assert a["peso_kg"] == 2634899004.0


async def test_leite_com_preco(api):
    resp = await api.get("/v1/sidra/leite")
    l = resp.json()["dados"][0]
    assert l["litros"] == 6780958000.0  # a fonte fala em mil litros; entregamos litros
    assert l["preco_medio"] == 2.24


async def test_municipios_campeoes(api):
    resp = await api.get("/v1/sidra/municipios?produto=soja&uf=MT&limit=3")
    corpo = resp.json()
    assert corpo["meta"]["uf"] == "MT"
    assert corpo["dados"][0]["localidade"] == "Sorriso (MT)"
    assert corpo["dados"][0]["valor"] == 2084520.0


async def test_municipios_exige_uf(api):
    resp = await api.get("/v1/sidra/municipios?produto=soja")
    assert resp.status_code == 400


async def test_conab_safra_ultimo_levantamento(api):
    resp = await api.get("/v1/conab/safra")
    corpo = resp.json()
    # só o ano agrícola corrente (2025/26) e o levantamento mais novo (9º)
    assert corpo["meta"]["ano_agricola"] == "2025/26"
    assert corpo["meta"]["levantamento"] == "9º LEV"
    por_produto = {d["produto"]: d for d in corpo["dados"]}
    # as duas safras de milho somadas: 800 + 52000
    assert por_produto["Milho"]["producao_mil_t"] == 52800.0
    # soja MT+PR somadas: 45000 + 22000
    assert por_produto["Soja"]["producao_mil_t"] == 67000.0
    assert corpo["dados"][0]["produto"] == "Soja"  # maior primeiro


async def test_conab_safra_por_uf(api):
    resp = await api.get("/v1/conab/safra?uf=PR&produto=soja")
    d = resp.json()["dados"][0]
    assert d["uf"] == "PR"
    assert d["producao_mil_t"] == 22000.0
    assert d["produtividade"] == 3.79


async def test_conab_precos_pega_o_mes_mais_novo_por_uf(api):
    resp = await api.get("/v1/conab/precos?produto=soja")
    corpo = resp.json()
    por_uf = {d["uf"]: d for d in corpo["dados"]}
    # MT tem maio e junho: fica junho; decimal com vírgula vira float
    assert por_uf["MT"]["periodo"] == "2026-06"
    assert por_uf["MT"]["valor_kg"] == 2.12
    assert por_uf["PR"]["valor_kg"] == 2.27
    # o nível ATACADO ficou de fora (só produtor)
    assert all("Produtor" in (d["nivel"] or "") for d in corpo["dados"])
