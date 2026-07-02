async def test_ons_geracao_soma_o_sin(api):
    resp = await api.get("/v1/ons/geracao")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["meta"]["tempo_real"] is True
    assert corpo["meta"]["fonte"]["nome"].startswith("ONS")

    sin = corpo["dados"][0]
    assert sin["regiao"] == "SIN"
    # SIN = soma dos 4 subsistemas (Itaipu conta como hidráulica no SE/CO)
    assert sin["hidraulica"] == 42900.0
    assert sin["eolica"] == 19580.0
    assert sin["geracao_total"] == 73882.0
    assert sin["carga"] == 73000.0
    # renovável = (hidráulica + eólica + solar) / total
    assert sin["renovavel_pct"] == 84.6


async def test_ons_traz_os_subsistemas(api):
    resp = await api.get("/v1/ons/geracao")
    dados = resp.json()["dados"]
    regioes = {d["regiao"] for d in dados}
    assert regioes == {"SIN", "Sudeste/Centro-Oeste", "Sul", "Nordeste", "Norte"}


async def test_ons_pula_o_registro_zerado(api):
    # a fixture termina com um minuto zerado (o ONS publica o próximo antes de
    # ter o dado); o instante escolhido deve ser o último com geração real
    resp = await api.get("/v1/ons/geracao")
    assert resp.json()["meta"]["instante"].startswith("2026-07-01T20:48")


async def test_ons_e_tempo_real_nao_cacheia(api):
    resp = await api.get("/v1/ons/geracao")
    # fonte ao vivo: não carimba cache hit
    assert resp.json()["meta"].get("cache") in (None, "ao vivo")


async def test_ons_recurso_desconhecido_da_404(api):
    resp = await api.get("/v1/ons/turbinas")
    assert resp.status_code == 404
