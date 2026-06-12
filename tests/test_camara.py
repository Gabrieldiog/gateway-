async def test_deputados_normalizados(api):
    resp = await api.get("/v1/camara/deputados?uf=SP&itens=3")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["fonte"] == "camara"
    assert corpo["total"] == 3
    primeiro = corpo["dados"][0]
    assert set(primeiro) >= {"id", "nome", "partido", "uf", "foto"}
    assert primeiro["uf"] == "SP"


async def test_deputado_detalhe_mesmo_schema_da_lista(api):
    resp = await api.get("/v1/camara/deputados/204528")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["total"] == 1
    detalhe = corpo["dados"][0]
    assert detalhe["id"] == 204528
    assert detalhe["nome"]
    assert detalhe["uf"] == "SP"


async def test_despesas_normalizadas(api):
    resp = await api.get("/v1/camara/deputados/204528/despesas?ano=2025")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["total"] == 3
    despesa = corpo["dados"][0]
    assert despesa["deputado_id"] == 204528
    assert despesa["fornecedor_doc"] == "00000000000010"
    assert despesa["data"] == "2024-12-22"
    # valor vem como string decimal, nunca float
    assert despesa["valor"] == "275.0"


async def test_despesa_suja_sai_limpa(api):
    resp = await api.get("/v1/camara/deputados/204528/despesas?ano=2025")
    suja = resp.json()["dados"][2]
    # cnpj mascarado vira so digitos, texto perde espacos e ponto final,
    # data nula e url vazia viram None sem quebrar nada
    assert suja["fornecedor_doc"] == "12345678000190"
    assert suja["tipo"] == "COMBUSTÍVEIS E LUBRIFICANTES"
    assert suja["data"] is None
    assert suja["url_documento"] is None


async def test_votacoes_normalizadas(api):
    resp = await api.get("/v1/camara/votacoes?itens=3")
    assert resp.status_code == 200
    votacao = resp.json()["dados"][0]
    assert set(votacao) >= {"id", "data", "descricao", "aprovada"}


async def test_proposicoes_normalizadas(api):
    resp = await api.get("/v1/camara/proposicoes?tipo=PL&ano=2025")
    assert resp.status_code == 200
    proposicao = resp.json()["dados"][0]
    assert proposicao["tipo"] == "PL"
    assert proposicao["ementa"]


async def test_param_desconhecido_da_400_com_lista_dos_aceitos(api):
    resp = await api.get("/v1/camara/deputados?cidade=Campinas")
    assert resp.status_code == 400
    corpo = resp.json()
    assert "uf" in corpo["detalhes"]["parametros_aceitos"]


async def test_recurso_desconhecido_da_404_com_recursos_disponiveis(api):
    resp = await api.get("/v1/camara/nao-existe")
    assert resp.status_code == 404
    assert "deputados" in resp.json()["detalhes"]["recursos_disponiveis"]


async def test_404_da_fonte_vira_404_nosso(api):
    resp = await api.get("/v1/camara/deputados/999999999")
    assert resp.status_code == 404
    assert resp.json()["detalhes"]["status_upstream"] == 404
