"""Toda a suite roda offline: o httpx recebe um MockTransport que responde
com as fixturas gravadas em tests/fixtures, entao nenhum teste abre socket."""

import json
from pathlib import Path

import httpx
import pytest
from httpx import ASGITransport, MockTransport

from balcao.cache import CacheRespostas
from balcao.connectors.base import connector_classes
from balcao.main import create_app

FIXTURES = Path(__file__).parent / "fixtures"

# prefixo de URL -> fixture; os mais especificos vem primeiro
ROTAS_FAKE = [
    ("https://dadosabertos.camara.leg.br/api/v2/deputados/204528/despesas", "camara_despesas"),
    ("https://dadosabertos.camara.leg.br/api/v2/deputados/204528", "camara_deputado_detalhe"),
    ("https://dadosabertos.camara.leg.br/api/v2/deputados/999999999", None),
    ("https://dadosabertos.camara.leg.br/api/v2/deputados", "camara_deputados"),
    ("https://dadosabertos.camara.leg.br/api/v2/votacoes", "camara_votacoes"),
    ("https://dadosabertos.camara.leg.br/api/v2/proposicoes", "camara_proposicoes"),
    ("https://api.bcb.gov.br/dados/serie/bcdata.sgs.432", "bacen_selic"),
    ("https://servicodados.ibge.gov.br/api/v1/localidades/estados/SP/municipios", "ibge_municipios_sp"),
    ("https://servicodados.ibge.gov.br/api/v1/localidades/estados", "ibge_estados"),
    ("https://legis.senado.leg.br/dadosabertos/senador/lista/atual", "senado_lista"),
]


def carrega_fixture(nome: str) -> dict | list:
    return json.loads((FIXTURES / f"{nome}.json").read_text(encoding="utf-8"))


def responde_fake(request: httpx.Request) -> httpx.Response:
    url = str(request.url)
    for prefixo, nome in ROTAS_FAKE:
        if url.startswith(prefixo):
            if nome is None:
                return httpx.Response(404, json={"detail": "nao existe"})
            return httpx.Response(200, json=carrega_fixture(nome))
    return httpx.Response(500, json={"erro": f"sem fixture pra {url}"})


def monta_app():
    app = create_app()
    # o ASGITransport nao roda o lifespan, entao o estado e montado na mao
    cliente_fake = httpx.AsyncClient(transport=MockTransport(responde_fake))
    app.state.client = cliente_fake
    app.state.cache = CacheRespostas(ttl=600)
    app.state.connectors = {
        nome: cls(cliente_fake) for nome, cls in connector_classes().items()
    }
    return app, cliente_fake


@pytest.fixture
async def api():
    app, cliente_fake = monta_app()
    transporte = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transporte, base_url="http://teste") as cliente:
        yield cliente
    await cliente_fake.aclose()
