async def test_lista_estabelecimentos(api):
    resp = await api.get("/v1/sus/estabelecimentos?uf=SP&tipo=5")
    assert resp.status_code == 200
    corpo = resp.json()
    # 3 no bruto, o registro sem codigo_cnes é descartado
    assert corpo["total"] == 2
    assert corpo["meta"]["descartados"] == 1

    hc = corpo["dados"][0]
    assert hc["cnes"] == 2077485
    assert hc["tipo"] == "HOSPITAL GERAL"  # código 5 vira o nome do tipo
    assert hc["uf"] == "SP"  # codigo_uf 35 vira a sigla
    assert hc["cnpj"] == "60448040000139"
    assert hc["email"] == "contato@hc.gov.br"  # minúsculo e sem espaço sobrando
    assert hc["endereco"] == "AV DR ENEAS DE CARVALHO AGUIAR, 255"


async def test_cnpj_cai_pra_entidade_e_nome_limpo(api):
    resp = await api.get("/v1/sus/estabelecimentos?municipio=350160")
    ubs = next(d for d in resp.json()["dados"] if d["cnes"] == 9629963)
    assert ubs["nome"] == "UBS VILA MEDON"  # espaços duplicados aplainados
    assert ubs["tipo"] == "CENTRO DE SAUDE/UNIDADE BASICA"
    # numero_cnpj veio nulo, cai pro numero_cnpj_entidade
    assert ubs["cnpj"] == "19550205000179"


async def test_uf_invalida_da_400(api):
    resp = await api.get("/v1/sus/estabelecimentos?uf=XX")
    assert resp.status_code == 400


async def test_param_desconhecido_da_400(api):
    resp = await api.get("/v1/sus/estabelecimentos?cidade=campinas")
    assert resp.status_code == 400


async def test_detalhe_por_cnes(api):
    resp = await api.get("/v1/sus/estabelecimentos/2077485")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["total"] == 1
    assert corpo["dados"][0]["nome"] == "HOSPITAL DAS CLINICAS"


async def test_sus_aparece_em_fontes(api):
    resp = await api.get("/v1/fontes")
    nomes = {f["nome"] for f in resp.json()["fontes"]}
    assert "sus" in nomes
