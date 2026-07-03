import httpx
import pytest
from httpx import MockTransport

from balcao.cache import CacheRespostas
from balcao.connectors.camara import CamaraConnector
from balcao.exceptions import ErroUpstream
from balcao.resilience import CircuitBreaker

from conftest import carrega_fixture, monta_app


def cliente_que_falha(vezes: int, corpo_ok) -> tuple[httpx.AsyncClient, dict]:
    """Responde 503 nas primeiras `vezes` chamadas e 200 depois."""
    contagem = {"chamadas": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        contagem["chamadas"] += 1
        if contagem["chamadas"] <= vezes:
            return httpx.Response(503, json={"erro": "fora do ar"})
        return httpx.Response(200, json=corpo_ok)

    return httpx.AsyncClient(transport=MockTransport(handler)), contagem


async def test_retry_recupera_falha_passageira():
    cliente, contagem = cliente_que_falha(2, carrega_fixture("camara_deputados"))
    conector = CamaraConnector(cliente, retry_tentativas=3)
    resposta = await conector.fetch("deputados")
    assert resposta.total == 3
    assert contagem["chamadas"] == 3


async def test_retry_esgotado_vira_erro_upstream():
    cliente, contagem = cliente_que_falha(99, {})
    conector = CamaraConnector(cliente, retry_tentativas=2)
    with pytest.raises(ErroUpstream):
        await conector.fetch("deputados")
    assert contagem["chamadas"] == 2


async def test_breaker_abre_e_para_de_chamar_a_fonte():
    cliente, contagem = cliente_que_falha(99, {})
    breaker = CircuitBreaker(limite_falhas=2, cooldown=30.0)
    conector = CamaraConnector(cliente, retry_tentativas=1, breaker=breaker)

    for _ in range(2):
        with pytest.raises(ErroUpstream):
            await conector.fetch("deputados")
    assert breaker.aberto
    chamadas_antes = contagem["chamadas"]

    # circuito aberto: erro imediato, sem nem tentar a fonte — e o erro
    # ja diz em quantos segundos vale voltar
    with pytest.raises(ErroUpstream) as exc:
        await conector.fetch("deputados")
    assert contagem["chamadas"] == chamadas_antes
    assert exc.value.detalhes.get("circuito") == "aberto"
    assert exc.value.detalhes.get("passageiro") is True
    assert 0 < exc.value.detalhes.get("tente_em_s") <= 30


async def test_breaker_fecha_depois_do_cooldown():
    relogio = {"agora": 0.0}
    cliente, _ = cliente_que_falha(2, carrega_fixture("camara_deputados"))
    breaker = CircuitBreaker(limite_falhas=2, cooldown=30.0, timer=lambda: relogio["agora"])
    conector = CamaraConnector(cliente, retry_tentativas=1, breaker=breaker)

    for _ in range(2):
        with pytest.raises(ErroUpstream):
            await conector.fetch("deputados")
    assert breaker.aberto

    # passado o cooldown a sondagem acontece, da certo e fecha o circuito
    relogio["agora"] = 31.0
    resposta = await conector.fetch("deputados")
    assert resposta.total == 3
    assert not breaker.aberto


async def test_fonte_caida_serve_do_cache_stale():
    app, cliente_fake = monta_app()
    relogio = {"agora": 0.0}
    app.state.cache = CacheRespostas(
        ttl=600, stale_ttl=86400, timer=lambda: relogio["agora"]
    )
    transporte = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transporte, base_url="http://teste") as api:
        primeira = await api.get("/v1/ibge/estados")
        assert primeira.status_code == 200

        # o cache fresco venceu e a fonte morreu no meio tempo
        relogio["agora"] = 700.0
        morto = httpx.AsyncClient(
            transport=MockTransport(lambda r: httpx.Response(503, json={}))
        )
        ibge = app.state.connectors["ibge"]
        ibge.client = morto
        ibge.retry_tentativas = 1

        segunda = await api.get("/v1/ibge/estados")
        assert segunda.status_code == 200
        assert segunda.json()["meta"]["cache"] == "stale"
        assert "aviso" in segunda.json()["meta"]
        # o carimbo de honestidade: de quando e o dado servido do arquivo
        assert "salvo_em" in segunda.json()["meta"]
        assert segunda.json()["dados"] == primeira.json()["dados"]
        await morto.aclose()
    await cliente_fake.aclose()


async def test_upstream_200_com_html_vira_erro_upstream():
    # portal do governo em manutencao responde 200 com HTML; sem a guarda o
    # resp.json() estourava sem tratamento e o gateway devolvia 500 cru
    from balcao.connectors.ckan import AneelConnector

    cliente = httpx.AsyncClient(
        transport=MockTransport(
            lambda r: httpx.Response(200, text="<html>em manutencao</html>")
        )
    )
    conector = AneelConnector(cliente, retry_tentativas=1)
    with pytest.raises(ErroUpstream):
        await conector.fetch("datasets")
    await cliente.aclose()


async def test_fonte_caida_sem_stale_da_erro_limpo(api):
    # o conftest nao tem fixture pra esse caminho, entao o upstream da 500
    resp = await api.get("/v1/senado/senadores/9999")
    assert resp.status_code == 502
    corpo = resp.json()
    assert "erro" in corpo
    assert corpo["detalhes"]["fonte"] == "senado"
    # a falha se declara passageira e sugere quando tentar de novo
    assert corpo["detalhes"]["passageiro"] is True
    assert corpo["detalhes"]["tente_em_s"] > 0


def test_breaker_informa_quanto_falta():
    relogio = {"agora": 0.0}
    breaker = CircuitBreaker(limite_falhas=1, cooldown=30.0, timer=lambda: relogio["agora"])
    assert breaker.restante == 0.0
    breaker.registra_falha()
    assert breaker.aberto
    relogio["agora"] = 12.0
    assert breaker.restante == 18.0
    relogio["agora"] = 31.0
    assert breaker.restante == 0.0