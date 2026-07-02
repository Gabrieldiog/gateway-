"""Toda a suite roda offline: o httpx recebe um MockTransport que responde
com as fixturas gravadas em tests/fixtures, entao nenhum teste abre socket."""

import json
import os
import re
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

# fontes com chave (Transparencia, brapi) leem o token das settings; aqui vai
# um de mentira pra suite rodar identica em qualquer maquina, com ou sem .env
os.environ["TRANSPARENCIA_API_KEY"] = "chave-de-teste"
os.environ["BRAPI_TOKEN"] = "token-de-teste"

import httpx
import pytest
from httpx import ASGITransport, MockTransport

from balcao.arquivos import ArquivoVotos
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
    # Tesouro/SICONFI: mesmo path /dca, distingue pelo ente (id_ente) e pelo anexo
    if "siconfi/tt/dca" in url:
        q = parse_qs(urlparse(url).query)
        ente = q.get("id_ente", [""])[0]
        receita = "I-C" in url
        if ente == "1":
            fixture = "tesouro_uniao_receitas" if receita else "tesouro_uniao_despesas"
        elif len(ente) == 7:  # código IBGE de município
            fixture = "tesouro_municipio_receitas" if receita else "tesouro_municipio_despesas"
        else:  # ente de 2 dígitos = estado
            fixture = "tesouro_receitas" if receita else "tesouro_despesas"
        return httpx.Response(200, json=carrega_fixture(fixture))
    # AwesomeAPI (cotações em tempo real): /json/last/USD-BRL,EUR-BRL,...
    if "awesomeapi.com.br/json/last/" in url:
        return httpx.Response(200, json=carrega_fixture("cotacoes_last"))
    # Boletim Focus (Olinda/OData): devolve um registro sintético com o
    # indicador pedido no $filter, pra o painel poder testar as 5 séries
    if "servico/Expectativas" in url:
        alvo = re.search(r"Indicador eq '([^']+)'", unquote(url))
        return httpx.Response(200, json={"value": [{
            "Indicador": alvo.group(1) if alvo else "IPCA",
            "IndicadorDetalhe": None,
            "Data": "2026-06-26",
            "DataReferencia": "2026",
            "Media": 5.31,
            "Mediana": 5.33,
            "DesvioPadrao": 0.23,
            "Minimo": 4.3,
            "Maximo": 5.86,
            "numeroRespondentes": 148,
            "baseCalculo": 0,
        }]})
    # Portal da Transparencia — exige o header chave-api-dados; sem ele, 401
    if "api.portaldatransparencia.gov.br" in url:
        if not request.headers.get("chave-api-dados"):
            return httpx.Response(401, json={"Erro na API": "Chave de API não informada!"})
        if "/emendas" in url:
            return httpx.Response(200, json=carrega_fixture("transparencia_emendas"))
        if "/ceis" in url:
            return httpx.Response(200, json=carrega_fixture("transparencia_ceis"))
        if "/cnep" in url:
            return httpx.Response(200, json=carrega_fixture("transparencia_cnep"))
        if "novo-bolsa-familia-por-municipio" in url:
            return httpx.Response(200, json=carrega_fixture("transparencia_bolsa"))
    # Tesouro Direto — CSV de 14 MB sem ordem cronológica (fixture encolhida)
    if "tesourotransparente.gov.br" in url and "precotaxatesourodireto" in url:
        return httpx.Response(
            200, text=(FIXTURES / "tesourodireto.csv").read_text(encoding="utf-8")
        )
    # ComexStat — consulta por POST; o corpo diz a dimensão pedida
    if "api-comexstat.mdic.gov.br/general" in url:
        corpo = json.loads(request.content or b"{}")
        flow = corpo.get("flow", "export")
        if corpo.get("monthDetail"):
            fator = 1 if flow == "export" else 2
            lista = [
                {"year": "2026", "monthNumber": "05", "metricFOB": str(31904049589 // fator)},
                {"year": "2026", "monthNumber": "04", "metricFOB": str(34211323941 // fator)},
            ]
        elif "country" in corpo.get("details", []):
            lista = [
                {"year": "2026", "country": "China", "metricFOB": "46263322664", "metricKG": "1000"},
                {"year": "2026", "country": "Estados Unidos", "metricFOB": "14011988576", "metricKG": "500"},
            ]
        elif "state" in corpo.get("details", []):
            lista = [
                {"year": "2026", "state": "São Paulo", "metricFOB": "28171881259", "metricKG": "900"},
                {"year": "2026", "state": "Rio de Janeiro", "metricFOB": "22055659374", "metricKG": "800"},
            ]
        else:
            lista = [
                {"year": "2026", "chapterCode": "27", "chapter": "Combustíveis minerais", "metricFOB": "27242313613", "metricKG": "700"},
            ]
        return httpx.Response(200, json={"data": {"list": lista}, "success": True, "message": None})
    # InfoDengue — semanas epidemiológicas de um município
    if "info.dengue.mat.br/api/alertcity" in url:
        return httpx.Response(200, json=carrega_fixture("infodengue_alertas"))
    # brapi (B3) — exige Bearer; devolve um ativo sintético com o símbolo pedido
    if "brapi.dev/api/v2/stocks/quote" in url:
        if not request.headers.get("authorization", "").startswith("Bearer "):
            return httpx.Response(401, json={"error": True, "message": "Token de autenticação não fornecido"})
        simbolo = parse_qs(urlparse(url).query).get("symbols", [""])[0]
        return httpx.Response(200, json={"results": [{
            "requestedSymbol": simbolo,
            "symbol": simbolo,
            "data": {
                "shortName": simbolo,
                "longName": f"Empresa {simbolo}",
                "currency": "BRL",
                "regularMarketPrice": 171688.61 if simbolo == "^BVSP" else 37.83,
                "regularMarketChangePercent": -0.2,
                "regularMarketOpen": 37.5,
                "regularMarketDayHigh": 37.84,
                "regularMarketDayLow": 37.4,
                "regularMarketPreviousClose": 37.73,
                "regularMarketTime": "2026-07-02T12:21:41.000Z",
            },
        }]})
    # PNCP — consulta pública de licitações e contratos
    if "pncp.gov.br/api/consulta" in url:
        if "/contratacoes/publicacao" in url:
            return httpx.Response(200, json=carrega_fixture("pncp_contratacoes"))
        if "/contratos" in url:
            return httpx.Response(200, json=carrega_fixture("pncp_contratos"))
    # ONS — geração do SIN quase em tempo real (balanço energético do dia)
    if "tr.ons.org.br/Content/Get/BalancoEnergetico" in url:
        return httpx.Response(200, json=carrega_fixture("ons_balanco"))
    # INPE — arquivo CSV diário de focos de queimada (texto, não JSON)
    if "dataserver-coids.inpe.br" in url and "focos_diario_br_" in url:
        return httpx.Response(200, text=(FIXTURES / "inpe_focos.csv").read_text(encoding="utf-8"))
    # Câmara — arquivos anuais (histórico completo de votos por deputado)
    if "/arquivos/votacoesVotos/" in url:
        return httpx.Response(200, json=carrega_fixture("camara_arquivo_votos"))
    if "/arquivos/votacoes/" in url:
        return httpx.Response(200, json=carrega_fixture("camara_arquivo_votacoes"))
    # Senado (API nova de votação por parlamentar): histórico de um senador
    if "/dadosabertos/votacao" in url:
        return httpx.Response(200, json=carrega_fixture("senado_votos"))
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
    # /v1/votos varre N votações; qualquer /votacoes/{id}/votos não mapeada
    # acima cai no mesmo lote de votos (fan-out do histórico por deputado)
    if "/votacoes/" in url and url.endswith("/votos"):
        return httpx.Response(200, json=carrega_fixture("camara_votos"))
    # a 195 (índice diário da poupança) responde {"erro":{}} com HTTP 200 no
    # ultimos/1 — reproduz o quirk real pra provar que o conector não estoura
    if "api.bcb.gov.br/dados/serie/bcdata.sgs.195/" in url:
        return httpx.Response(200, json={"erro": {}})
    # BACEN SGS: a série 432 tem fixture própria (bacen_selic) no lote acima;
    # qualquer outra série (bcdata.sgs.{codigo}) serve pontos genéricos — o
    # painel de inflação puxa ~8 séries de uma vez
    if "api.bcb.gov.br/dados/serie/bcdata.sgs." in url:
        return httpx.Response(200, json=carrega_fixture("bacen_serie"))
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
    app.state.arquivo_votos = ArquivoVotos(cliente_fake)
    return app, cliente_fake


@pytest.fixture
async def api():
    app, cliente_fake = monta_app()
    transporte = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transporte, base_url="http://teste") as cliente:
        yield cliente
    await cliente_fake.aclose()
