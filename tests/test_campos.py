"""O ?campos= recorta cada item do envelope pros campos pedidos — vale pra
qualquer fonte, é aplicado na borda (inclusive sobre resposta cacheada)."""


async def test_campos_recorta_so_o_pedido(api):
    # 1ª chamada enche o cache; a 2ª (com campos) cai no hit e é recortada
    cheia = await api.get("/v1/camara/deputados?uf=SP")
    assert cheia.status_code == 200
    pedidos = list(cheia.json()["dados"][0].keys())[:2]

    resp = await api.get(f"/v1/camara/deputados?uf=SP&campos={','.join(pedidos)}")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["meta"]["projecao"] == pedidos
    assert corpo["meta"]["cache"] == "hit"
    for item in corpo["dados"]:
        assert list(item.keys()) == pedidos


async def test_campos_preserva_a_ordem_pedida(api):
    cheia = await api.get("/v1/camara/deputados")
    chaves = list(cheia.json()["dados"][0].keys())
    invertida = [chaves[1], chaves[0]]
    resp = await api.get(f"/v1/camara/deputados?campos={','.join(invertida)}")
    assert list(resp.json()["dados"][0].keys()) == invertida


async def test_campo_inexistente_da_400_com_aceitos(api):
    cheia = await api.get("/v1/camara/deputados")
    reais = set(cheia.json()["dados"][0].keys())
    resp = await api.get("/v1/camara/deputados?campos=nao_existe_mesmo")
    assert resp.status_code == 400
    aceitos = set(resp.json()["detalhes"]["parametros_aceitos"])
    assert reais <= aceitos


async def test_sem_campos_devolve_tudo(api):
    resp = await api.get("/v1/camara/deputados")
    assert "projecao" not in resp.json()["meta"]
    assert len(resp.json()["dados"][0]) >= 2
