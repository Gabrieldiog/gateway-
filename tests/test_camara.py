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


async def test_tramitacoes_traz_a_linha_do_tempo_com_o_marco(api):
    # PEC 3/2026 (do IPVA): a aprovação na CCJ é um evento da tramitação, que o
    # status atual (só a última linha) não conta. O recurso traz a linha do tempo.
    resp = await api.get("/v1/camara/proposicoes/2604173/tramitacoes")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["total"] > 0
    eventos = corpo["dados"]
    # a aprovação na CCJ está lá, com o marco traduzido pra fala de gente
    ccj = next(
        e for e in eventos if e["orgao"] == "CCJC" and e["descricao"] == "Aprovação do Parecer"
    )
    assert ccj["data"] == "2026-07-08"
    assert ccj["marco"] == "Aprovada na CCJ"
    # passo procedural não ganha marco falso (só ruído)
    leitura = next(e for e in eventos if e["descricao"] == "Leitura e publicação do Parecer")
    assert leitura["marco"] is None


def test_marco_humano_tira_o_sentido_do_despacho():
    # o marco de "aprovada/rejeitada" não pode sair só da descrição: a comissão
    # mata a matéria APROVANDO um parecer "pela rejeição"
    from balcao.connectors.camara import CamaraConnector

    c = CamaraConnector(None)
    # parecer favorável aprovado -> a matéria avança
    assert c._marco_humano("CCJC", "Aprovação do Parecer", "Aprovado o Parecer.") == "Aprovada na CCJ"
    # parecer aprovado PELA REJEIÇÃO -> a matéria morre (o "aprova" engana)
    assert (
        c._marco_humano("CCJC", "Aprovação do Parecer", "Aprovado o Parecer pela rejeição da matéria.")
        == "Rejeitada na CCJ"
    )
    assert c._marco_humano("CCJC", "Rejeição do Parecer", "Rejeitado.") == "Rejeitada na CCJ"
    # requerimento e leitura são procedurais, não viram marco
    assert c._marco_humano("CCJC", "Aprovação de Requerimento", "Aprovado.") is None
    assert c._marco_humano("CCJC", "Leitura e publicação do Parecer", None) is None
    # plenário e fim de linha
    assert c._marco_humano("PLEN", "Aprovação da Matéria", None) == "Aprovada em plenário"
    assert c._marco_humano("MESA", "Transformado em Norma Jurídica", None) == "Virou norma (lei)"


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
