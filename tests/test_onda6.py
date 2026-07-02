"""Senado matérias (API nova de processos) e TSE doações (zip file-backed)."""


async def test_senado_materias_normalizadas(api):
    resp = await api.get("/v1/senado/materias?tipo=PL&ano=2026")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["meta"]["tipo"] == "PL"
    # a mais movimentada recentemente vem primeiro
    m = corpo["dados"][0]
    assert m["identificacao"] == "PL 199/2026"
    assert m["tramitando"] is True
    assert m["situacao"] == "AGUARDANDO DESIGNAÇÃO DO RELATOR"
    assert m["atualizada_em"] == "2026-07-01"


async def test_senado_materias_filtra_tramitando(api):
    resp = await api.get("/v1/senado/materias?tramitando=nao")
    dados = resp.json()["dados"]
    assert len(dados) == 1
    assert dados[0]["identificacao"] == "PL 100/2026"


async def test_tse_doacoes_por_candidato(api):
    resp = await api.get("/v1/tse/doacoes?uf=GO&ano=2022")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["meta"]["fonte"]["nome"].startswith("TSE")
    assert corpo["meta"]["doacoes_total"] == 3
    # Beltrano (15000,50) na frente de Fulana (6000 + 4000)
    top = corpo["dados"][0]
    assert top["nome"] == "BELTRANO SOUZA"
    assert top["detalhe"] == "MDB · Governador"
    assert top["total"] == "15000.50"
    segunda = corpo["dados"][1]
    assert segunda["nome"] == "FULANA DA SILVA"
    assert segunda["total"] == "10000.00"
    assert segunda["doacoes"] == 2


async def test_tse_doacoes_por_doador_traz_documento(api):
    resp = await api.get("/v1/tse/doacoes?uf=GO&por=doador")
    top = resp.json()["dados"][0]
    assert top["nome"] == "JOÃO DOADOR"
    assert top["detalhe"] == "00903149133"
    assert top["total"] == "21000.50"


async def test_tse_sem_uf_da_400(api):
    resp = await api.get("/v1/tse/doacoes")
    assert resp.status_code == 400


async def test_tse_ano_sem_eleicao_da_400(api):
    resp = await api.get("/v1/tse/doacoes?uf=GO&ano=2023")
    assert resp.status_code == 400
