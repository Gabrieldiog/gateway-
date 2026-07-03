"""Onda F3 — Obrasgov: as obras federais, inclusive as paradas."""


async def test_obras_paralisadas_com_flag_de_atraso(api):
    resp = await api.get("/v1/obrasgov/obras?uf=GO&situacao=paralisada")
    assert resp.status_code == 200
    corpo = resp.json()
    o = corpo["dados"][0]
    assert o["situacao"] == "Paralisada"
    assert o["valor_previsto"] == "12500000.5"
    # fim previsto em 2024 e obra parada: atrasada
    assert o["atrasada"] is True
    assert o["empregos"] == 120
    # a concluída não é atrasada mesmo com fim previsto no passado
    concluida = corpo["dados"][1]
    assert concluida["atrasada"] is False
    assert concluida["valor_previsto"] is None  # a fonte deixa vazio mesmo
    # totalElements mente; o last é a verdade
    assert corpo["meta"]["tem_proxima"] is True


async def test_obras_situacao_invalida_da_400(api):
    resp = await api.get("/v1/obrasgov/obras?situacao=enrolada")
    assert resp.status_code == 400
    assert "paralisada" in resp.json()["detalhes"]["parametros_aceitos"]


async def test_obras_tolera_strings_vazias_da_fonte(api):
    # a fonte manda "" onde deveria ser null — nada de 500
    resp = await api.get("/v1/obrasgov/obras?uf=GO&situacao=paralisada")
    assert resp.status_code == 200
    creche = next(o for o in resp.json()["dados"] if "Creche" in o["nome"])
    assert creche["empregos"] is None
    assert creche["valor_previsto"] is None
    assert creche["atrasada"] is True
