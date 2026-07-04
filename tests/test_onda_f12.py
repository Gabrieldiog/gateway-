"""Onda F12 — Segurança: ocorrências criminais do Sinesp (base VDE)."""


async def test_panorama_agrega_e_ordena_por_total(api):
    resp = await api.get("/v1/seguranca/panorama?uf=SP&ano=2025")
    assert resp.status_code == 200
    corpo = resp.json()
    eventos = {i["evento"]: i for i in corpo["dados"]}
    # roubo de veículo (600+400=1000) vem antes de homicídio (10+5=15)
    assert corpo["dados"][0]["evento"] == "Roubo de veículo"
    assert eventos["Roubo de veículo"]["total"] == 1000
    assert eventos["Homicídio doloso"]["total"] == 15


async def test_crime_de_vitima_traz_recorte_por_sexo(api):
    resp = await api.get("/v1/seguranca/panorama?uf=SP&ano=2025")
    homicidio = next(i for i in resp.json()["dados"] if i["evento"] == "Homicídio doloso")
    # vítima: mostra sexo (fem 1, masc 9+5=14)
    assert homicidio["feminino"] == 1
    assert homicidio["masculino"] == 14
    # a série mensal também vem
    assert homicidio["meses"] == [{"mes": 1, "total": 10}, {"mes": 2, "total": 5}]


async def test_crime_de_ocorrencia_nao_inventa_sexo(api):
    resp = await api.get("/v1/seguranca/panorama?uf=SP&ano=2025")
    roubo = next(i for i in resp.json()["dados"] if i["evento"] == "Roubo de veículo")
    assert roubo["feminino"] is None
    assert roubo["masculino"] is None


async def test_eventos_administrativos_ficam_de_fora(api):
    # "Emissão de Alvarás" (bombeiro) e linha com total 0 não entram
    resp = await api.get("/v1/seguranca/panorama?uf=SP&ano=2025")
    eventos = [i["evento"] for i in resp.json()["dados"]]
    assert "Emissão de Alvarás de licença" not in eventos
    assert "Roubo de carga" not in eventos  # total 0 na fixture


async def test_ranking_por_100k_compara_estados_justo(api):
    resp = await api.get("/v1/seguranca/ranking?crime=homicidio&ano=2025")
    corpo = resp.json()
    # CE (100 em 8,79 mi hab) tem taxa maior que SP (15 em 44,4 mi), mesmo com
    # muito menos gente — é o sentido de comparar por 100 mil
    assert corpo["dados"][0]["uf"] == "CE"
    assert corpo["dados"][0]["por_100k"] > corpo["dados"][1]["por_100k"]
    sp = next(i for i in corpo["dados"] if i["uf"] == "SP")
    assert sp["por_100k"] == round(15 / 44411238 * 100000, 1)


async def test_ano_padrao_e_o_ultimo_fechado(api):
    resp = await api.get("/v1/seguranca/panorama?uf=SP")
    # sem ano, usa o ano anterior (base do ano corrente é parcial)
    assert resp.json()["meta"]["ano_automatico"] is True


async def test_uf_e_crime_invalidos_dao_400(api):
    assert (await api.get("/v1/seguranca/panorama?uf=XX")).status_code == 400
    assert (await api.get("/v1/seguranca/panorama")).status_code == 400
    assert (await api.get("/v1/seguranca/ranking?crime=pixuleco")).status_code == 400
    assert (await api.get("/v1/seguranca/panorama?uf=SP&ano=1990")).status_code == 400
