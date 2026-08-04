"""Onda F6, Consumidor: o ranking oficial de reclamações do Banco Central."""


async def test_sem_ano_vem_o_periodo_mais_recente(api):
    resp = await api.get("/v1/bacen/reclamacoes")
    assert resp.status_code == 200
    corpo = resp.json()
    # o listing da fonte diz que o mais novo é o 1º trimestre de 2026
    assert corpo["meta"]["ano"] == 2026
    assert corpo["meta"]["periodo"] == 1
    assert corpo["meta"]["periodicidade"] == "TRIMESTRAL"
    assert corpo["dados"][0]["periodo"] == "1º trimestre de 2026"


async def test_posicao_so_vale_dentro_do_top15(api):
    resp = await api.get("/v1/bacen/reclamacoes")
    itens = {i["instituicao"]: i for i in resp.json()["dados"]}
    # C6 lidera o ranking oficial; índice com vírgula virou float
    assert itens["BANCO C6"]["posicao"] == 1
    assert itens["BANCO C6"]["indice"] == 55.3
    assert itens["NU PAGAMENTOS"]["posicao"] == 2
    # MT IP tem índice gigante (401 clientes!) mas NÃO entra na fila oficial
    assert itens["MT IP"]["top15"] is False
    assert itens["MT IP"]["posicao"] is None
    # instituição pequena sem índice: None, não zero
    assert itens["ABC-BRASIL"]["indice"] is None
    # o sufixo "(conglomerado)" saiu do nome
    assert "conglomerado" not in " ".join(itens)


async def test_grupo_top15_filtra_o_ranking_oficial(api):
    resp = await api.get("/v1/bacen/reclamacoes?grupo=top15")
    corpo = resp.json()
    assert corpo["total"] == 2
    assert all(i["top15"] for i in corpo["dados"])


async def test_busca_por_nome(api):
    resp = await api.get("/v1/bacen/reclamacoes?busca=agibank")
    corpo = resp.json()
    assert corpo["total"] == 1
    assert corpo["dados"][0]["indice"] == 218.64  # vírgula decimal normalizada
    assert corpo["dados"][0]["clientes"] == 7527488


async def test_ano_fora_do_listing_da_400_com_opcoes(api):
    resp = await api.get("/v1/bacen/reclamacoes?ano=1999")
    assert resp.status_code == 400
    assert "2026" in str(resp.json()["detalhes"])


async def test_consorcio_recua_ate_o_periodo_que_existe(api):
    # 2026 só tem ranking de bancos: pedir consórcio recua pra 2025/4º tri
    resp = await api.get("/v1/bacen/reclamacoes?tipo=consorcios")
    corpo = resp.json()
    assert corpo["meta"]["ano"] == 2025
    assert corpo["meta"]["periodo"] == 4


async def test_consorcio_fala_outro_dialeto_de_colunas(api):
    resp = await api.get("/v1/bacen/reclamacoes?tipo=consorcios")
    itens = resp.json()["dados"]
    ademicon = next(i for i in itens if "ADEMICON" in i["instituicao"])
    # "Administradora de consórcio" + "reclamações reguladas procedentes" +
    # "clientes Consorciados", e sem coluna Categoria o ranking é um só
    assert ademicon["posicao"] == 1
    assert ademicon["indice"] == 34.56
    assert ademicon["reclamacoes_procedentes"] == 17
    assert ademicon["clientes"] == 491794
    sem_indice = next(i for i in itens if "GAZIN" in i["instituicao"])
    assert sem_indice["indice"] is None
    assert sem_indice["posicao"] is None
