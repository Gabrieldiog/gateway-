async def test_health(api):
    resp = await api.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_fontes_lista_os_conectores(api):
    resp = await api.get("/v1/fontes")
    assert resp.status_code == 200
    corpo = resp.json()
    nomes = {f["nome"] for f in corpo["fontes"]}
    assert nomes == {"camara", "senado", "bacen", "brasilapi", "conab", "diarios", "focus", "ibge", "sus", "tesouro", "sidra", "aneel", "mme", "antt", "ipeadata", "obrasgov", "cotacoes", "ons", "inpe", "transparencia", "pncp", "b3", "infodengue", "comex", "tesourodireto", "anp", "datajud", "tse"}
    camara = next(f for f in corpo["fontes"] if f["nome"] == "camara")
    assert "deputados" in camara["recursos"]


async def test_fonte_desconhecida_da_404_com_fontes_disponiveis(api):
    resp = await api.get("/v1/nasa/foguetes")
    assert resp.status_code == 404
    assert "camara" in resp.json()["detalhes"]["fontes_disponiveis"]


async def test_cabecalhos_de_seguranca(api):
    resp = await api.get("/health")
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["x-frame-options"] == "DENY"
    assert resp.headers["referrer-policy"] == "no-referrer"


async def test_segunda_chamada_vem_do_cache(api):
    primeira = await api.get("/v1/ibge/estados")
    assert "cache" not in primeira.json()["meta"]
    segunda = await api.get("/v1/ibge/estados")
    assert segunda.json()["meta"]["cache"] == "hit"
    # o corpo cacheado continua igual, fora o carimbo de cache
    assert segunda.json()["dados"] == primeira.json()["dados"]
