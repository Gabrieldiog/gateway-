async def test_bacen_novas_series_por_apelido(api):
    # as séries de inflação que faltavam (IPCA 12m, INPC, IGP-DI, poupança)
    for apelido, codigo in (("ipca12m", 13522), ("inpc", 188), ("igpdi", 190), ("poupanca", 196)):
        resp = await api.get(f"/v1/bacen/{apelido}?ultimos=2")
        assert resp.status_code == 200, apelido
        ponto = resp.json()["dados"][0]
        assert ponto["serie"] == codigo
        assert ponto["nome"] == apelido


async def test_bacen_painel_inflacao(api):
    resp = await api.get("/v1/bacen/inflacao")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["meta"]["painel"] == "custo de vida"
    # selo de procedência: a resposta diz de onde o dado vem
    assert corpo["meta"]["fonte"]["nome"].startswith("Banco Central")
    chaves = {ind["chave"] for ind in corpo["dados"]}
    # o painel junta os indicadores que pesam no bolso numa chamada só
    assert {"ipca12m", "igpm", "selic", "dolar"} <= chaves
    ind = next(i for i in corpo["dados"] if i["chave"] == "dolar")
    assert ind["nome"] == "Dólar (PTAX)"
    assert ind["unidade"] == "R$"
    assert "valor" in ind and "data" in ind


async def test_bacen_serie_com_erro_nao_estoura(api):
    # a série 195 devolve {"erro":{}} com 200; o conector trata como vazio
    resp = await api.get("/v1/bacen/serie/195?ultimos=1")
    assert resp.status_code == 200
    assert resp.json()["dados"] == []


async def test_bacen_painel_tambem_responde_por_painel(api):
    # "inflacao" e "painel" apontam pro mesmo lugar
    a = (await api.get("/v1/bacen/inflacao")).json()
    b = (await api.get("/v1/bacen/painel")).json()
    assert {i["chave"] for i in a["dados"]} == {i["chave"] for i in b["dados"]}
