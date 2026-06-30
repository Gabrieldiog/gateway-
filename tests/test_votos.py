async def test_votos_nominais_com_placar(api):
    resp = await api.get("/v1/camara/votacoes/2629954-8/votos")
    assert resp.status_code == 200
    corpo = resp.json()
    # 5 votos no bruto, um sem id de deputado é descartado
    assert corpo["total"] == 4
    assert corpo["meta"]["descartados"] == 1
    assert corpo["meta"]["placar"] == {"Sim": 1, "Não": 1, "Abstenção": 1, "Obstrução": 1}

    v0 = corpo["dados"][0]
    assert v0["votacao_id"] == "2629954-8"
    assert v0["voto"] == "Sim"
    assert v0["deputado"] == "Arnaldo Jardim"

    # UF minúscula vira maiúscula e nome com espaços duplicados é aplainado
    maria = next(d for d in corpo["dados"] if d["deputado_id"] == 204560)
    assert maria["uf"] == "RJ"
    assert maria["deputado"] == "Maria Silva"


async def test_votacao_simbolica_avisa(api):
    resp = await api.get("/v1/camara/votacoes/9999999-9/votos")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["total"] == 0
    assert "aviso" in corpo["meta"]
    assert "placar" not in corpo["meta"]


async def test_detalhe_da_votacao(api):
    resp = await api.get("/v1/camara/votacoes/2629954-8")
    assert resp.status_code == 200
    v = resp.json()["dados"][0]
    assert v["id"] == "2629954-8"
    assert v["orgao"] == "PLEN"
    assert v["aprovada"] is True


# --- /v1/votos: o histórico por deputado (resolve + fan-out nas votações) ---


async def test_votos_por_deputado_resolve_e_varre(api):
    resp = await api.get("/v1/votos?parlamentar=204528")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["fonte"] == "camara"
    assert corpo["casa"] == "camara"
    assert corpo["parlamentar"]["nome"]  # resolveu o deputado pelo id
    # a fixture de votações traz 3; o fan-out varre todas
    assert corpo["analisadas"] == 3
    assert isinstance(corpo["votos"], list)
    assert corpo["total"] == len(corpo["votos"])


async def test_votos_por_deputado_cacheia(api):
    primeira = await api.get("/v1/votos?parlamentar=204528")
    segunda = await api.get("/v1/votos?parlamentar=204528")
    assert segunda.status_code == 200
    assert segunda.json() == primeira.json()


async def test_votos_historico_ano_completo(api):
    # com ?ano=, vem do arquivo anual (histórico inteiro), não do scan recente
    resp = await api.get("/v1/votos?parlamentar=204528&casa=camara&ano=2024")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["casa"] == "camara"
    assert corpo["parlamentar"]["nome"]
    assert corpo["total"] == 2  # o deputado 204528 tem 2 votos no arquivo
    # juntou a descrição da votação (do outro arquivo)
    assert any("emenda" in v["descricao"].lower() for v in corpo["votos"])
    assert {v["voto"] for v in corpo["votos"]} == {"Sim", "Não"}
    # mais recente primeiro
    assert corpo["votos"][0]["data"] >= corpo["votos"][-1]["data"]


async def test_votos_por_senador(api):
    resp = await api.get("/v1/votos?parlamentar=Alan&casa=senado")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["casa"] == "senado"
    assert corpo["parlamentar"]["nome"] == "Alan Rick"
    # a fixture traz 3 votos; o Senado entrega o histórico inteiro (sem fan-out)
    assert corpo["total"] == 3
    votos = {v["voto"] for v in corpo["votos"]}
    assert "Sim" in votos and "Não" in votos
    # voto secreto vira "Votou" e fica marcado
    secreto = next(v for v in corpo["votos"] if v["voto"] == "Votou")
    assert secreto["secreta"] is True
