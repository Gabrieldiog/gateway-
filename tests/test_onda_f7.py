"""Onda F7 — Almanaque: as loterias da CAIXA e os nomes do Censo."""


async def test_resultado_da_mega_normalizado(api):
    resp = await api.get("/v1/loterias/resultado")
    assert resp.status_code == 200
    d = resp.json()["dados"][0]
    assert d["nome_jogo"] == "Mega-Sena"
    assert d["concurso"] == 3026
    assert d["data"] == "2026-07-02"  # dd/mm/aaaa virou ISO
    assert d["dezenas"] == ["14", "19", "42", "45", "48", "54"]
    assert d["acumulado"] is True
    assert d["estimativa_proximo"] == "33000000.0"
    assert d["premios"][1] == {"faixa": "5 acertos", "ganhadores": 40, "valor": "37029.54"}


async def test_dupla_sena_tem_segundo_sorteio(api):
    resp = await api.get("/v1/loterias/resultado?jogo=duplasena")
    d = resp.json()["dados"][0]
    assert d["dezenas_2"] == ["05", "17", "22", "26", "36", "38"]
    assert d["cidades_ganhadoras"] == [{"municipio": "GOIANIA", "uf": "GO", "ganhadores": 1}]


async def test_jogo_desconhecido_da_400(api):
    resp = await api.get("/v1/loterias/resultado?jogo=jogodobicho")
    assert resp.status_code == 400
    assert "megasena" in str(resp.json()["detalhes"])


async def test_nome_por_decada_soma_o_total(api):
    resp = await api.get("/v1/ibge/nomes?nome=gabriel")
    corpo = resp.json()
    assert corpo["meta"]["total_pessoas"] == 1267 + 271405 + 584024
    decadas = {i["decada"]: i["frequencia"] for i in corpo["dados"]}
    # "[2000,2010[" virou "2000"; "1930[" virou "até 1930"
    assert decadas["2000"] == 584024
    assert decadas["até 1930"] == 1267


async def test_nome_por_uf_ordena_por_forca_e_traduz_codigo(api):
    resp = await api.get("/v1/ibge/nomes?nome=gabriel&por=uf")
    itens = resp.json()["dados"]
    # código IBGE 53 = DF, que lidera por 100 mil hab; código desconhecido cai fora
    assert itens[0]["uf"] == "DF"
    assert itens[0]["por_100k"] == 662.8
    assert all(i["uf"] != "99" for i in itens)


async def test_nome_raro_avisa_em_vez_de_quebrar(api):
    resp = await api.get("/v1/ibge/nomes?nome=zzz")
    corpo = resp.json()
    assert corpo["dados"] == []
    assert "Censo 2010" in corpo["meta"]["aviso"]


async def test_nome_com_numero_da_400(api):
    resp = await api.get("/v1/ibge/nomes?nome=r2d2")
    assert resp.status_code == 400


async def test_ranking_dos_nomes(api):
    resp = await api.get("/v1/ibge/nomes/ranking?decada=1990&limit=2")
    itens = resp.json()["dados"]
    assert itens[0] == {"fonte": "ibge", "posicao": 1, "nome": "MARIA", "frequencia": 915119}
    assert len(itens) == 2


async def test_ranking_decada_quebrada_da_400(api):
    resp = await api.get("/v1/ibge/nomes/ranking?decada=1995")
    assert resp.status_code == 400
