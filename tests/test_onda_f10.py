"""Onda F10 — Educação: IDEB e Censo Escolar por município (via IBGE)."""


async def test_ideb_traz_as_tres_etapas_em_serie(api):
    resp = await api.get("/v1/educacao/ideb?municipio=3550308")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["meta"]["rede"] == "publica"
    assert corpo["total"] == 3
    iniciais = corpo["dados"][0]
    assert iniciais["etapa"] == "Anos iniciais (1º ao 5º)"
    assert iniciais["ultimo_ano"] == 2023
    assert iniciais["ultimo_valor"] == 5.9
    # a série vem ordenada por ano
    assert [p["ano"] for p in iniciais["serie"]] == [2005, 2015, 2021, 2023]


async def test_ideb_ignora_ano_sem_nota(api):
    # o Censo tem "2013": "-" na fixture do fundamental — não entra na série
    resp = await api.get("/v1/educacao/censo?municipio=3550308")
    fundamental = next(i for i in resp.json()["dados"] if "fundamental" in i["etapa"].lower())
    anos = [p["ano"] for p in fundamental["serie"]]
    assert 2013 not in anos
    assert fundamental["ultimo_ano"] == 2025
    assert fundamental["ultimo_valor"] == 1334975.0


async def test_rede_municipal_sem_medio_devolve_serie_vazia(api):
    resp = await api.get("/v1/educacao/ideb?municipio=3550308&rede=municipal")
    medio = next(i for i in resp.json()["dados"] if i["etapa"] == "Ensino médio")
    # prefeitura não oferece ensino médio: série vazia, sem inventar valor
    assert medio["serie"] == []
    assert medio["ultimo_valor"] is None
    assert medio["rede"] == "municipal"


async def test_censo_matriculas_por_etapa(api):
    resp = await api.get("/v1/educacao/censo?municipio=3550308&tema=matriculas")
    etapas = {i["etapa"]: i for i in resp.json()["dados"]}
    assert etapas["Educação infantil"]["ultimo_valor"] == 540000.0
    assert etapas["Ensino médio"]["ultimo_valor"] == 440000.0


async def test_municipio_invalido_da_400(api):
    assert (await api.get("/v1/educacao/ideb?municipio=123")).status_code == 400
    assert (await api.get("/v1/educacao/ideb?municipio=abcdefg")).status_code == 400


async def test_rede_e_tema_invalidos_dao_400(api):
    assert (await api.get("/v1/educacao/ideb?municipio=3550308&rede=comunitaria")).status_code == 400
    assert (await api.get("/v1/educacao/censo?municipio=3550308&tema=merenda")).status_code == 400
