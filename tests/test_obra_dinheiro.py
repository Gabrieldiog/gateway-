"""O follow-the-money das obras: a cascata que resolve o favorecido dos
empenhos que o Obrasgov devolve vazio, e o contrato da empreiteira final."""


async def test_cascata_acha_a_nota_no_csv_e_o_favorecido_no_siafi(api):
    resp = await api.get("/v1/obra/dinheiro?id=11370.52-41")
    assert resp.status_code == 200
    corpo = resp.json()
    e = corpo["empenhos"][0]
    # a nota veio do CSV do SICONV (casada por UG + valor numérico)
    assert e["nota"] == "2019NE802642"
    assert e["data"] == "2019-12-02"
    # e com ela o SIAFI entregou o favorecido com CNPJ e o autor da emenda
    assert e["origem"] == "siafi"
    assert e["favorecido"] == "MUNICIPIO DE DOVERLANDIA"
    assert e["favorecido_doc"] == "00078790000128"
    assert e["autor_emenda"] == "DANIEL VILELA"
    assert e["modalidade"] == "transferência a município"


async def test_sem_siafi_a_regra_orcamentaria_aponta_o_executor(api):
    resp = await api.get("/v1/obra/dinheiro?id=11370.52-41")
    e = resp.json()["empenhos"][1]
    # UG com gestão própria: o SIAFI responde vazio, mas natureza 444042 é
    # transferência a município — o favorecido É o executor da obra
    assert e["origem"] == "repasse"
    assert e["favorecido"] == "MUNICIPIO DE DOVERLANDIA"
    # o codigo do executor vira CNPJ com zfill
    assert e["favorecido_doc"] == "00078790000128"


async def test_movimentacao_interna_nao_inventa_favorecido(api):
    resp = await api.get("/v1/obra/dinheiro?id=11370.52-41")
    e = resp.json()["empenhos"][2]
    assert e["origem"] == "interno"
    assert e["favorecido"] is None
    assert e["modalidade"] == "movimentação interna"


async def test_contrato_final_vem_do_csv_do_siconv(api):
    resp = await api.get("/v1/obra/dinheiro?id=11370.52-41")
    corpo = resp.json()
    c = corpo["contratos"][0]
    assert c["fornecedor"] == "PROJETOS E CONSTRUTORA SUPREMA EIRELI"
    assert c["cnpj"] == "40223985000139"
    assert c["valor"] == "488031.68"  # vírgula decimal do CSV normalizada
    assert c["modalidade_licitacao"] == "Tomada de Preços"
    assert c["assinatura"] == "2021-10-14"  # dd/mm/aaaa virou ISO
    assert c["situacao"] == "Concluído"
    assert corpo["total_empenhado"] == "582500.0"
    assert corpo["erros"] == {}


async def test_favorecido_da_propria_fonte_tem_prioridade(api):
    # obra de execução direta: o Obrasgov já traz o favorecido — a cascata
    # não sobrescreve
    resp = await api.get("/v1/obra/dinheiro?id=33266.16-49")
    corpo = resp.json()
    for e in corpo["empenhos"]:
        assert e["origem"] == "obrasgov"
        assert e["favorecido"] == "CONSTRUTORA EXEMPLO LTDA"
        assert e["modalidade"] == "aplicação direta"
    # essa obra não está nos CSVs do SICONV: sem contrato, sem invenção
    assert corpo["contratos"] == []


async def test_documento_siafi_normalizado(api):
    resp = await api.get("/v1/transparencia/documento?codigo=175004000012019NE802642")
    assert resp.status_code == 200
    d = resp.json()["dados"][0]
    assert d["favorecido"] == "MUNICIPIO DE DOVERLANDIA"
    assert d["favorecido_doc"] == "00078790000128"
    assert d["valor"] == "477500.00"  # "477.500,00" da fonte
    assert d["data"] == "2019-12-02"
    assert d["autor_emenda"] == "DANIEL VILELA"  # sem o código "3081 - "
    assert d["modalidade"] == "40 - Transferências a Municípios"


async def test_documento_inexistente_vira_aviso_nao_erro(api):
    # a fonte responde 200 com corpo VAZIO pra documento que não existe
    resp = await api.get("/v1/transparencia/documento?codigo=153080000012020NE999999")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["dados"] == []
    assert "não encontrado" in corpo["meta"]["aviso"]


async def test_documento_codigo_invalido_da_400(api):
    resp = await api.get("/v1/transparencia/documento?codigo=abc")
    assert resp.status_code == 400


async def test_nota_nao_cruza_entre_empenhos_de_mesmo_valor(api):
    # o CSV tem uma armadilha: linha de mesma UG e mesmo valor (R$5000) do
    # empenho interno, mas natureza de repasse — sem casar natureza, a nota
    # 2021NE111111 grudaria no empenho errado
    resp = await api.get("/v1/obra/dinheiro?id=11370.52-41")
    interno = resp.json()["empenhos"][2]
    assert interno["natureza"] == "449151"
    assert interno["nota"] is None
    assert interno["favorecido"] is None


async def test_cpf_mascarado_nao_vira_documento(api):
    # pagamento a pessoa física: o Portal mascara o CPF (***.171.572-**) —
    # o fragmento de 6 dígitos não pode ser publicado como documento
    resp = await api.get("/v1/transparencia/documento?codigo=154003152792025OB001266")
    d = resp.json()["dados"][0]
    assert d["favorecido"] == "FULANO DE TAL"
    assert d["favorecido_doc"] is None
    assert d["autor_emenda"] is None  # autor vazio não vira string vazia


async def test_sem_chave_da_transparencia_degrada_pra_regra(api):
    # chave vazia = fonte desativada por config: a cascata cai pra regra de
    # repasse sem registrar erro (a resposta continua cacheável e correta)
    from conftest import monta_app
    from httpx import ASGITransport
    import httpx as _httpx

    app, cliente_fake = monta_app()
    app.state.connectors["transparencia"]._chave = ""
    async with _httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://teste"
    ) as cliente:
        resp = await cliente.get("/v1/obra/dinheiro?id=11370.52-41")
    await cliente_fake.aclose()
    corpo = resp.json()
    assert corpo["erros"] == {}
    e = corpo["empenhos"][0]
    # sem SIAFI, o repasse resolve pelo executor — e sem autor de emenda
    assert e["origem"] == "repasse"
    assert e["favorecido"] == "MUNICIPIO DE DOVERLANDIA"
    assert "autor_emenda" not in e or e["autor_emenda"] is None
