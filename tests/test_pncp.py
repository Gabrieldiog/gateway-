async def test_licitacoes_normalizadas(api):
    resp = await api.get("/v1/pncp/licitacoes?de=2026-06-20&ate=2026-06-30")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["meta"]["fonte"]["nome"].startswith("PNCP")
    assert corpo["meta"]["total_registros"] == 10041
    assert corpo["meta"]["tem_proxima"] is True
    lic = corpo["dados"][0]
    assert lic["orgao"] == "MUNICIPIO DE LINDOESTE"
    assert lic["uf"] == "PR"
    assert lic["esfera"] == "municipal"
    assert lic["modalidade"] == "Pregão - Eletrônico"
    assert float(lic["valor_estimado"]) == 127296.0
    # datetime da fonte vira só a data
    assert lic["publicada_em"] == "2026-06-20"
    assert lic["propostas_ate"] == "2026-07-07"


async def test_licitacoes_modalidade_por_slug(api):
    resp = await api.get("/v1/pncp/licitacoes?modalidade=dispensa")
    assert resp.status_code == 200


async def test_licitacoes_modalidade_invalida_da_400(api):
    resp = await api.get("/v1/pncp/licitacoes?modalidade=cartas-marcadas")
    assert resp.status_code == 400
    assert "pregao-eletronico" in resp.json()["detalhes"]["parametros_aceitos"]


async def test_licitacoes_periodo_invertido_da_400(api):
    resp = await api.get("/v1/pncp/licitacoes?de=2026-06-30&ate=2026-06-01")
    assert resp.status_code == 400


async def test_contratos_normalizados(api):
    resp = await api.get("/v1/pncp/contratos?de=2026-06-25&ate=2026-06-30")
    assert resp.status_code == 200
    c = resp.json()["dados"][0]
    assert c["fornecedor"] == "PR COMÉRCIO DE ARTIGOS PARA BEBÊS LTDA"
    assert c["fornecedor_doc"] == "59196088000101"
    assert c["uf"] == "SC"
    assert float(c["valor"]) == 1070.0
    assert c["assinado_em"] == "2026-06-24"
