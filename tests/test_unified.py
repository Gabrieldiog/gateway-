import httpx
from httpx import MockTransport

from conftest import monta_app


async def test_buscar_junta_resultados_de_varias_fontes(api):
    resp = await api.get("/v1/buscar?q=alan&fontes=camara,senado")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["fontes_consultadas"] == ["camara", "senado"]
    tipos = {r["tipo_resultado"] for r in corpo["resultados"]}
    # a camara devolve deputados e proposicoes, o senado devolve senadores
    assert "deputado" in tipos
    assert "senador" in tipos
    assert corpo["erros"] == {}


async def test_buscar_municipio_pelo_ibge(api):
    resp = await api.get("/v1/buscar?q=adamantina&fontes=ibge")
    assert resp.status_code == 200
    nomes = [r["nome"] for r in resp.json()["resultados"]]
    assert "Adamantina" in nomes


async def test_buscar_serie_economica_pelo_apelido(api):
    resp = await api.get("/v1/buscar?q=selic&fontes=bacen")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["total"] > 0
    assert all(r["tipo_resultado"] == "serie_economica" for r in corpo["resultados"])
    assert all(r["serie"] == 432 for r in corpo["resultados"])


async def test_buscar_fonte_desconhecida_da_404(api):
    resp = await api.get("/v1/buscar?q=teste&fontes=tse")
    assert resp.status_code == 404


async def test_fonte_caida_nao_derruba_a_busca():
    app, cliente_fake = monta_app()
    morto = httpx.AsyncClient(
        transport=MockTransport(lambda r: httpx.Response(503, json={}))
    )
    senado = app.state.connectors["senado"]
    senado.client = morto
    senado.retry_tentativas = 1

    transporte = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transporte, base_url="http://teste") as api:
        resp = await api.get("/v1/buscar?q=alan&fontes=camara,senado")
        assert resp.status_code == 200
        corpo = resp.json()
        # a camara respondeu mesmo com o senado fora
        assert corpo["total"] > 0
        assert "senado" in corpo["erros"]
    await morto.aclose()
    await cliente_fake.aclose()


async def test_gastos_por_id_agrega_por_tipo(api):
    resp = await api.get("/v1/gastos?deputado=204528&ano=2025")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["deputado"]["id"] == 204528
    assert corpo["total_documentos"] == 3
    # 275.0 + 275.0 + 180.5 da fixture
    assert corpo["valor_total"] == "730.5"
    assert len(corpo["por_tipo"]) == 2


async def test_gastos_resolve_deputado_por_nome(api):
    resp = await api.get("/v1/gastos?deputado=Adriana&ano=2025")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["deputado"]["id"] in {221328, 204528, 204554}
    assert corpo["valor_total"] == "730.5"
