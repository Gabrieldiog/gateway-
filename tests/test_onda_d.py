"""Onda D — enriquecer: os recursos de detalhe que transformam lista em
história (perfil, discursos, orientações, itens de compra, juros por banco,
documentos de emenda e a Ficha do Fornecedor)."""


async def test_perfil_do_deputado(api):
    resp = await api.get("/v1/camara/deputados/204528/perfil")
    assert resp.status_code == 200
    p = resp.json()["dados"][0]
    assert p["nome"] == "Adriana Ventura"
    assert p["escolaridade"] == "Doutorado"
    assert p["naturalidade"] == "São Paulo · SP"
    assert p["gabinete"] == "prédio 4 · sala 802"
    assert p["telefone_gabinete"] == "3215-5802"
    assert len(p["redes"]) == 3
    assert p["condicao"] == "Titular"


async def test_discursos_com_transcricao(api):
    resp = await api.get("/v1/camara/deputados/204528/discursos?itens=2")
    assert resp.status_code == 200
    d = resp.json()["dados"][0]
    assert d["tipo"] == "DISCUSSÃO"
    assert "merenda" in d["sumario"]
    assert d["transcricao"].startswith("O SR. DEPUTADO")
    assert d["url_video"].startswith("https://www.youtube.com")
    assert d["evento"] == "Ordem do Dia"


async def test_orientacoes_de_bancada(api):
    resp = await api.get("/v1/camara/votacoes/2629954-8/orientacoes")
    assert resp.status_code == 200
    bancadas = {o["bancada"]: o["orientacao"] for o in resp.json()["dados"]}
    assert bancadas["PT"] == "Sim"
    assert bancadas["Governo"] == "Sim"
    assert bancadas["NOVO"] == "Liberado"


async def test_despesa_traz_nota_fiscal_e_glosa(api):
    resp = await api.get("/v1/camara/deputados/204528/despesas?ano=2025")
    d = resp.json()["dados"][0]
    assert d["url_documento"].endswith(".pdf")
    assert d["valor_documento"] == "275.0"
    assert d["valor_glosa"] == "0.0"
    assert d["fornecedor"].startswith("Adobe")


async def test_emenda_documentos(api):
    resp = await api.get("/v1/transparencia/emendas/documentos?codigo=202538950005")
    assert resp.status_code == 200
    docs = resp.json()["dados"]
    assert docs[0]["fase"] == "Empenho"
    assert docs[0]["documento_resumido"] == "2025NE000310"
    # data dd/mm/aaaa da fonte sai ISO
    assert docs[0]["data"] == "2025-03-15"


async def test_contratos_federais_por_cnpj(api):
    resp = await api.get("/v1/transparencia/contratos?documento=04.984.400/0001-30")
    assert resp.status_code == 200
    contratos = resp.json()["dados"]
    assert len(contratos) == 2
    assert contratos[0]["orgao"] == "Presidência da República"
    assert contratos[0]["valor"] == "240000.00"
    assert contratos[0]["inicio"] == "2023-01-10"


async def test_vinculos_dossie_por_cnpj(api):
    resp = await api.get("/v1/transparencia/vinculos?cnpj=04984400000130")
    assert resp.status_code == 200
    d = resp.json()["dados"][0]
    assert d["razao_social"].startswith("CTA")
    assert "possuiContratacao" in d["vinculos"]
    assert d["flags"]["sancionadoCEIS"] is False


async def test_brasilapi_ficha_de_cnpj(api):
    resp = await api.get("/v1/brasilapi/cnpj/04.984.400/0001-30")
    assert resp.status_code == 200
    f = resp.json()["dados"][0]
    assert f["razao_social"].startswith("CTA")
    assert f["situacao"] == "ATIVA"
    assert f["socios"] == ["CLEITON SILVA", "MARIA SILVA"]
    assert f["abertura"] == "2002-03-15"


async def test_juros_bancos_corta_na_ultima_janela(api):
    resp = await api.get("/v1/bacen/juros-bancos?modalidade=rotativo")
    assert resp.status_code == 200
    corpo = resp.json()
    # a fixture tem 3 linhas da janela 15-19/jun e 1 da anterior: corta na nova
    assert corpo["total"] == 3
    assert corpo["meta"]["janela_de"] == "2026-06-15"
    assert corpo["meta"]["janela_ate"] == "2026-06-19"
    assert corpo["dados"][0]["posicao"] == 1
    assert corpo["dados"][0]["instituicao"].startswith("BANCO EXEMPLO BARATO")
    assert corpo["dados"][2]["taxa_ano"] == 481.62


async def test_pncp_itens_da_compra(api):
    resp = await api.get("/v1/pncp/itens?controle=76205699000198-1-000072/2026")
    assert resp.status_code == 200
    itens = resp.json()["dados"]
    assert itens[0]["descricao"].startswith("ADITIVO")
    assert itens[0]["tem_resultado"] is True
    assert itens[0]["valor_unitario"] == "1367.63"
    assert itens[1]["tem_resultado"] is False


async def test_pncp_vencedor_do_item(api):
    resp = await api.get("/v1/pncp/resultado?controle=76205699000198-1-000072/2026&item=1")
    assert resp.status_code == 200
    v = resp.json()["dados"][0]
    assert v["fornecedor"] == "AUTO PECAS EXEMPLO LTDA"
    assert v["porte"] == "EPP"
    assert v["valor_total"] == "64900.0"
    assert v["desconto_pct"] == 5.09


async def test_pncp_controle_invalido_da_400(api):
    resp = await api.get("/v1/pncp/itens?controle=banana")
    assert resp.status_code == 400


async def test_ficha_do_fornecedor_junta_quatro_fontes(api):
    resp = await api.get("/v1/fornecedor/04.984.400/0001-30")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["cnpj"] == "04984400000130"
    # cadastro da Receita via BrasilAPI
    assert corpo["cadastro"]["razao_social"].startswith("CTA")
    # dossiê de vínculos da Transparência
    assert "possuiContratacao" in corpo["vinculos"]["vinculos"]
    # sanções (CEIS+CNEP das fixtures) e contratos federais
    assert len(corpo["sancoes"]) == 2
    assert len(corpo["contratos"]) == 2
    assert corpo["erros"] == {}
