async def test_precos_por_estado_ordena_mais_barato_primeiro(api):
    resp = await api.get("/v1/anp/precos?combustivel=gasolina")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["meta"]["fonte"]["nome"].startswith("ANP")
    assert corpo["meta"]["coletas_de"] == "02/06/2026"
    assert corpo["meta"]["coletas_ate"] == "26/06/2026"
    # SP (5,80) mais barato que GO (média de 6,00/6,50/7,00 = 6,50)
    assert [e["local"] for e in corpo["dados"]] == ["SP", "GO"]
    go = corpo["dados"][1]
    assert go["preco_medio"] == "6.50"
    assert go["preco_minimo"] == "6.00"
    assert go["preco_maximo"] == "7.00"
    assert go["coletas"] == 3
    assert go["unidade"] == "R$ / litro"


async def test_precos_por_municipio_com_uf(api):
    resp = await api.get("/v1/anp/precos?combustivel=gasolina&por=municipio&uf=GO")
    corpo = resp.json()
    locais = {m["local"] for m in corpo["dados"]}
    # o campo com ';' embutido entre aspas não quebra o parser
    assert locais == {"GOIANIA", "ANAPOLIS"}
    goiania = next(m for m in corpo["dados"] if m["local"] == "GOIANIA")
    assert goiania["uf"] == "GO"
    assert goiania["preco_medio"] == "6.25"


async def test_gasolina_aditivada_e_produto_separado(api):
    resp = await api.get("/v1/anp/precos?combustivel=gasolina-aditivada")
    corpo = resp.json()
    assert corpo["total"] == 1
    assert corpo["dados"][0]["produto"] == "GASOLINA ADITIVADA"
    assert corpo["dados"][0]["preco_medio"] == "5.99"


async def test_combustivel_invalido_da_400(api):
    resp = await api.get("/v1/anp/precos?combustivel=querosene")
    assert resp.status_code == 400
    assert "diesel-s10" in resp.json()["detalhes"]["parametros_aceitos"]
