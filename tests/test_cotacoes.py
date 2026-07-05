"""Cotações em tempo real (AwesomeAPI). Fonte tempo-real: passa por um cache
CURTO (cache_vivo_ttl), fresco de segundos mas sem martelar a AwesomeAPI, que
rate-limita (429) um IP fixo consultando a cada request."""


async def test_cotacoes_last(api):
    resp = await api.get("/v1/cotacoes/last/USD-BRL,EUR-BRL,BTC-BRL")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["total"] == 3
    por_moeda = {c["moeda"]: c for c in corpo["dados"]}
    dolar = por_moeda["USD"]
    assert dolar["par"] == "USD/BRL"
    assert dolar["compra"] == "5.1796"
    assert dolar["venda"] == "5.1806"
    assert dolar["variacao_pct"] == -0.15
    assert dolar["atualizado"] == "2026-06-30 16:53:26"


async def test_cotacoes_par_invalido_da_400(api):
    resp = await api.get("/v1/cotacoes/last/DOLAR")
    assert resp.status_code == 400


async def test_cotacoes_cache_curto(api):
    # fonte tempo-real: a 1ª chamada busca fresco (miss), a 2ª idêntica volta
    # do cache curto (hit) — é o que segura o rate limit da AwesomeAPI sem
    # perder o frescor de segundos
    primeira = await api.get("/v1/cotacoes/last/USD-BRL")
    segunda = await api.get("/v1/cotacoes/last/USD-BRL")
    assert segunda.status_code == 200
    assert primeira.json()["meta"].get("cache") is None
    assert segunda.json()["meta"].get("cache") == "hit"


async def test_cotacoes_aparece_em_fontes(api):
    resp = await api.get("/v1/fontes")
    nomes = {f["nome"] for f in resp.json()["fontes"]}
    assert "cotacoes" in nomes
