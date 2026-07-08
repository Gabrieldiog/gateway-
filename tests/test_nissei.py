async def test_produtos_normalizados(api):
    resp = await api.get("/v1/nissei/produtos?termo=dipirona")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["meta"]["fonte"]["nome"] == "Farmácias Nissei"
    p = corpo["dados"][0]
    # o mais barato primeiro: EMS valor_fim R$6,50 < Medley R$9,29
    assert p["descricao"].startswith("Dipirona Sódica 500mg")
    assert p["valor"] == "6.50"
    assert p["valor_tabela"] == "12.00"  # o "de"
    assert p["estabelecimento"] == "Farmácias Nissei"
    assert p["municipio"] == "Goiânia"
    assert p["uf"] == "GO"
    assert p["preco_tipo"] == "local"


async def test_usa_o_valor_fim_nao_o_ini(api):
    # o preco praticado e o valor_fim (com desconto), nao o valor_ini ("de")
    resp = await api.get("/v1/nissei/produtos?termo=dipirona")
    medley = next(d for d in resp.json()["dados"] if "Medley" in d["descricao"])
    assert medley["valor"] == "9.29"
    assert medley["valor_tabela"] == "23.44"


async def test_fora_de_estoque_e_ignorado(api):
    # o fixture tem 3 produtos, mas um esta is_disponivel=false -> so 2 voltam
    resp = await api.get("/v1/nissei/produtos?termo=dipirona")
    corpo = resp.json()
    assert corpo["total"] == 2
    assert all("Fora de Estoque" not in d["descricao"] for d in corpo["dados"])


async def test_sem_termo_da_400(api):
    resp = await api.get("/v1/nissei/produtos")
    assert resp.status_code == 400


async def test_recurso_invalido_da_404(api):
    resp = await api.get("/v1/nissei/inexistente")
    assert resp.status_code == 404
