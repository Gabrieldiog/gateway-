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
    ("https://dadosabertos.camara.leg.br/api/v2/deputados/221328/despesas", "camara_despesas"),
    ("https://dadosabertos.camara.leg.br/api/v2/deputados/204528", "camara_deputado_detalhe"),
    ("https://dadosabertos.camara.leg.br/api/v2/deputados/999999999", None),
    ("https://dadosabertos.camara.leg.br/api/v2/deputados", "camara_deputados"),
    ("https://dadosabertos.camara.leg.br/api/v2/votacoes/2629954-8/votos", "camara_votos"),
    ("https://dadosabertos.camara.leg.br/api/v2/votacoes/9999999-9/votos", "camara_votos_vazio"),
    ("https://dadosabertos.camara.leg.br/api/v2/votacoes/2629954-8", "camara_votacao_detalhe"),
    ("https://dadosabertos.camara.leg.br/api/v2/votacoes", "camara_votacoes"),
    ("https://dadosabertos.camara.leg.br/api/v2/proposicoes", "camara_proposicoes"),
    ("https://api.bcb.gov.br/dados/serie/bcdata.sgs.432", "bacen_selic"),
    ("https://servicodados.ibge.gov.br/api/v1/localidades/estados/SP/municipios", "ibge_municipios_sp"),
    ("https://servicodados.ibge.gov.br/api/v1/localidades/municipios", "ibge_municipios_sp"),
    ("https://servicodados.ibge.gov.br/api/v1/localidades/estados", "ibge_estados"),
    ("https://legis.senado.leg.br/dadosabertos/senador/lista/atual", "senado_lista"),
    ("https://apidadosabertos.saude.gov.br/cnes/estabelecimentos/2077485", "sus_estabelecimento"),
    ("https://apidadosabertos.saude.gov.br/cnes/estabelecimentos", "sus_estabelecimentos"),
    ("https://apisidra.ibge.gov.br/values/t/1612", "sidra_producao"),
    ("https://apisidra.ibge.gov.br/values/t/3939", "sidra_rebanho"),
    ("http://www.ipeadata.gov.br/api/odata4/Metadados", "ipeadata_series"),
    ("http://www.ipeadata.gov.br/api/odata4/ValoresSerie", "ipeadata_valores"),
]


def carrega_fixture(nome: str) -> dict | list:
    return json.loads((FIXTURES / f"{nome}.json").read_text(encoding="utf-8"))


def responde_fake(request: httpx.Request) -> httpx.Response:
    url = str(request.url)
    # Tesouro/SICONFI: mesmo path /dca, distingue pelo anexo na query
    if "siconfi/tt/dca" in url:
        fixture = "tesouro_receitas" if "I-C" in url else "tesouro_despesas"
        return httpx.Response(200, json=carrega_fixture(fixture))
    # CKAN (ANEEL, MME, ANTT): mesma API em hosts diferentes, distingue pela ação
    if "/api/3/action/package_search" in url:
        return httpx.Response(200, json=carrega_fixture("ckan_datasets"))
    if "/api/3/action/datastore_search" in url:
        return httpx.Response(200, json=carrega_fixture("ckan_datastore"))
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
