"""Onda F11, Trabalho: desemprego e renda da PNAD Contínua (SIDRA)."""


async def test_desemprego_brasil_vem_em_ordem_cronologica(api):
    resp = await api.get("/v1/sidra/desemprego?ultimos=4")
    assert resp.status_code == 200
    corpo = resp.json()
    # a série sobe do trimestre mais antigo pro mais novo
    periodos = [i["periodo"] for i in corpo["dados"]]
    assert periodos[0] == "2º trimestre 2025"
    assert periodos[-1] == "1º trimestre 2026"
    assert corpo["meta"]["periodo"] == "1º trimestre 2026"
    assert corpo["dados"][-1]["unidade"] == "%"
    assert corpo["dados"][-1]["valor"] == 6.1


async def test_desemprego_por_uf_ranqueia_do_pior_pro_melhor(api):
    resp = await api.get("/v1/sidra/desemprego?por=uf")
    corpo = resp.json()
    assert corpo["total"] == 27
    pior, melhor = corpo["dados"][0], corpo["dados"][-1]
    # o código IBGE da UF vira sigla
    assert pior["uf"] and melhor["uf"]
    assert pior["valor"] >= melhor["valor"]


async def test_rendimento_real_em_reais(api):
    resp = await api.get("/v1/sidra/rendimento?ultimos=3")
    corpo = resp.json()
    ultimo = corpo["dados"][-1]
    assert ultimo["unidade"] == "R$"
    assert "real" in ultimo["indicador"].lower()
    assert ultimo["valor"] == 3726.0
    # trimestre móvel
    assert ultimo["periodo"] == "mar-abr-mai 2026"


async def test_por_invalido_da_400(api):
    resp = await api.get("/v1/sidra/desemprego?por=cidade")
    assert resp.status_code == 400
    assert "brasil" in str(resp.json()["detalhes"])


async def test_ultimos_fora_do_range_da_400(api):
    assert (await api.get("/v1/sidra/desemprego?ultimos=99")).status_code == 400
    assert (await api.get("/v1/sidra/rendimento?tipo=fantasia")).status_code == 400
