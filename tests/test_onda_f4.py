"""Onda F4, ANA/SAR: quanta água tem nos reservatórios do país."""


async def test_principais_junta_os_grandes(api):
    resp = await api.get("/v1/ana/principais")
    assert resp.status_code == 200
    corpo = resp.json()
    # 10 pedidos, todos respondem com a fixture, e normalizados
    assert corpo["meta"]["pedidos"] == 10
    assert corpo["total"] == 10
    m = corpo["dados"][0]
    assert m["reservatorio"] == "ITAIPU"
    assert m["volume_util_pct"] == 98.32  # a fonte manda como STRING "98.32"
    assert m["data"] == "2026-07-02"  # dd/MM/yyyy virou ISO
    assert m["afluencia"] == 9284.22


async def test_agora_deduz_o_sistema_pelo_codigo(api):
    resp = await api.get("/v1/ana/agora?codigo=29001")
    assert resp.status_code == 200
    m = resp.json()["dados"][0]
    assert m["sistema"] == "cantareira"
    assert m["codigo"] == "29001"


async def test_agora_sem_codigo_da_400(api):
    resp = await api.get("/v1/ana/agora")
    assert resp.status_code == 400


async def test_lista_sin_ignora_o_dropdown_de_estados(api):
    resp = await api.get("/v1/ana/reservatorios")
    assert resp.status_code == 200
    corpo = resp.json()
    # a página tem 2 options de estado (valor < 1000) que não são reservatório
    assert corpo["total"] == 5
    nomes = [r["nome"] for r in corpo["dados"]]
    assert "ITAIPU" in nomes
    assert "EMBORCAÇÃO" in nomes  # entity &#199; decodificada
    assert all(r["uf"] is None for r in corpo["dados"])


async def test_lista_nordeste_extrai_uf_do_nome(api):
    resp = await api.get("/v1/ana/reservatorios?sistema=nordeste&uf=CE")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["total"] == 2  # ACAUÃ é (PB), fica de fora
    r = corpo["dados"][0]
    assert r["uf"] == "CE"
    assert "(" not in r["nome"]  # o "(CE)" saiu do nome


async def test_lista_busca_por_trecho(api):
    resp = await api.get("/v1/ana/reservatorios?busca=serra")
    assert resp.json()["dados"][0]["nome"] == "SERRA DA MESA"


async def test_historico_sin_parseia_pelo_cabecalho(api):
    resp = await api.get("/v1/ana/historico?codigo=19058&dias=7")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["total"] == 2
    m = corpo["dados"][0]
    assert m["data"] == "2026-06-30"
    assert m["cota"] == 220.32  # vírgula decimal da tabela
    assert m["afluencia"] == 9045.05
    # Itaipu deixa o Volume Útil (%) em branco na tabela do SIN
    assert m["volume_util_pct"] is None


async def test_historico_cantareira_tem_colunas_diferentes(api):
    resp = await api.get("/v1/ana/historico?codigo=29001&dias=7")
    corpo = resp.json()
    m = corpo["dados"][0]
    # a tabela do Cantareira traz o volume em hm³ além do percentual
    assert m["volume_util_pct"] == 41.58
    assert m["volume_hm3"] == 335.95
    assert m["reservatorio"] == "JAGUARI-JACAREÍ"


async def test_historico_dias_fora_do_range_da_400(api):
    resp = await api.get("/v1/ana/historico?codigo=19058&dias=365")
    assert resp.status_code == 400
    assert "1..90" in str(resp.json()["detalhes"])


async def test_historico_nordeste_e_a_terceira_tabela(api):
    resp = await api.get("/v1/ana/historico?codigo=12112&dias=7")
    corpo = resp.json()
    m = corpo["dados"][0]
    # o Nordeste fala "Volume (%)" e tem "Capacidade (hm³)", que NÃO é volume
    assert m["volume_util_pct"] == 33.22
    assert m["volume_hm3"] == 2225.82
    assert m["cota"] == 91.56
    assert m["afluencia"] is None  # essa tabela não traz afluência
