"""Toda a suite roda offline: o httpx recebe um MockTransport que responde
com as fixturas gravadas em tests/fixtures, entao nenhum teste abre socket."""

import json
import os
import re
import tempfile
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

# fontes com chave (Transparencia, brapi) leem o token das settings; aqui vai
# um de mentira pra suite rodar identica em qualquer maquina, com ou sem .env
os.environ["TRANSPARENCIA_API_KEY"] = "chave-de-teste"
os.environ["BRAPI_TOKEN"] = "token-de-teste"
os.environ["DATAJUD_API_KEY"] = "chave-publica-de-teste"

import httpx
import pytest
from httpx import ASGITransport, MockTransport

from balcao.arquivos import ArquivoVotos
from balcao.cache import CacheRespostas
from balcao.connectors.base import connector_classes
from balcao.main import create_app
from balcao.siconv import ArquivosSiconv

FIXTURES = Path(__file__).parent / "fixtures"

# prefixo de URL -> fixture; os mais especificos vem primeiro
ROTAS_FAKE = [
    ("https://dadosabertos.camara.leg.br/api/v2/deputados/204528/despesas", "camara_despesas"),
    ("https://dadosabertos.camara.leg.br/api/v2/deputados/221328/despesas", "camara_despesas"),
    ("https://dadosabertos.camara.leg.br/api/v2/deputados/204528/discursos", "camara_discursos"),
    ("https://dadosabertos.camara.leg.br/api/v2/deputados/204528", "camara_deputado_detalhe"),
    ("https://dadosabertos.camara.leg.br/api/v2/deputados/999999999", None),
    ("https://dadosabertos.camara.leg.br/api/v2/deputados", "camara_deputados"),
    ("https://dadosabertos.camara.leg.br/api/v2/votacoes/2629954-8/votos", "camara_votos"),
    ("https://dadosabertos.camara.leg.br/api/v2/votacoes/9999999-9/votos", "camara_votos_vazio"),
    ("https://dadosabertos.camara.leg.br/api/v2/votacoes/2629954-8/orientacoes", "camara_orientacoes"),
    ("https://dadosabertos.camara.leg.br/api/v2/votacoes/2629954-8", "camara_votacao_detalhe"),
    ("https://brasilapi.com.br/api/cnpj/v1/", "brasilapi_cnpj"),
    ("https://api.obrasgov.gestao.gov.br/obrasgov/api/execucao-financeira?idProjetoInvestimento=11370.52-41", "obrasgov_execucao_doverlandia"),
    ("https://api.obrasgov.gestao.gov.br/obrasgov/api/execucao-financeira", "obrasgov_execucao"),
    ("https://api.obrasgov.gestao.gov.br/obrasgov/api/projeto-investimento", "obrasgov_obras"),
    ("https://api.queridodiario.ok.org.br/gazettes", "qd_gazettes"),
    ("https://api.queridodiario.ok.org.br/cities", "qd_cities"),
    ("https://dadosabertos.camara.leg.br/api/v2/votacoes", "camara_votacoes"),
    ("https://dadosabertos.camara.leg.br/api/v2/proposicoes/2234666", "camara_proposicao_detalhe"),
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
    ("https://apisidra.ibge.gov.br/values/t/6588", "sidra_safra"),
    ("https://apisidra.ibge.gov.br/values/t/1092", "sidra_abate"),
    ("https://apisidra.ibge.gov.br/values/t/1093", "sidra_abate"),
    ("https://apisidra.ibge.gov.br/values/t/1094", "sidra_abate"),
    ("https://apisidra.ibge.gov.br/values/t/1086", "sidra_leite"),
    ("https://apisidra.ibge.gov.br/values/t/5457", "sidra_municipios"),
    ("https://apisidra.ibge.gov.br/values/t/4709", "sidra_censo_pop"),
    ("https://apisidra.ibge.gov.br/values/t/4712", "sidra_censo_dom"),
    ("https://apisidra.ibge.gov.br/values/t/5938", "sidra_pib"),
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
    # BCB Olinda — ranking de juros por banco (taxaJuros v2)
    if "servico/taxaJuros" in url:
        return httpx.Response(200, json=carrega_fixture("bacen_juros"))
    # ANA/SAR — última medição é JSON; lista e histórico são páginas HTML
    if "ana.gov.br/sar/restportal" in url:
        return httpx.Response(200, json=carrega_fixture("ana_ultima"))
    if "ana.gov.br/sar0/" in url:
        if "dataInicial" in url:
            if "Reservatorios=29" in url:
                arquivo = "ana_historico_cant.html"
            elif "Reservatorios=12" in url:
                arquivo = "ana_historico_ne.html"
            else:
                arquivo = "ana_historico_sin.html"
        else:
            arquivo = "ana_dropdown_ne.html" if url.endswith("/Medicao") else "ana_dropdown_sin.html"
        return httpx.Response(200, content=(FIXTURES / arquivo).read_bytes())
    # CONAB — arquivos TXT em latin-1 (o conector decodifica dos bytes)
    if "portaldeinformacoes.conab.gov.br" in url:
        arquivo = "conab_levantamento.txt" if "LevantamentoGraos" in url else "conab_precos.txt"
        return httpx.Response(200, content=(FIXTURES / arquivo).read_bytes())
    # Obrasgov — a consulta por idUnico devolve a ficha de UMA obra
    if "obrasgov/api/projeto-investimento" in url and "idUnico=" in url:
        return httpx.Response(200, json=carrega_fixture("obrasgov_obra_detalhe"))
    # SICONV — os CSVs diários zipados que ligam a obra ao dinheiro
    if "repositorio.dados.gov.br/seges/detru" in url:
        arquivo = "siconv_contrato.zip" if "contrato" in url else "siconv_empenho.zip"
        return httpx.Response(200, content=(FIXTURES / arquivo).read_bytes())
    # PNCP operacional (/api/pncp): itens, resultado por item e arquivos
    if "pncp.gov.br/api/pncp/v1/orgaos" in url:
        if "/resultados" in url:
            return httpx.Response(200, json=carrega_fixture("pncp_resultado"))
        if "/arquivos" in url:
            return httpx.Response(200, json=carrega_fixture("pncp_arquivos"))
        return httpx.Response(200, json=carrega_fixture("pncp_itens"))
    if "api.portaldatransparencia.gov.br" in url:
        if not request.headers.get("chave-api-dados"):
            return httpx.Response(401, json={"Erro na API": "Chave de API não informada!"})
        if "/emendas/documentos" in url:
            return httpx.Response(200, json=carrega_fixture("transparencia_emendas_documentos"))
        if "/despesas/documentos/" in url:
            # só o empenho de Doverlândia e um pagamento a pessoa física
            # existem; o resto responde como a fonte real: 200 com corpo vazio
            if url.endswith("/175004000012019NE802642"):
                return httpx.Response(200, json=carrega_fixture("transparencia_documento"))
            if url.endswith("/154003152792025OB001266"):
                return httpx.Response(200, json=carrega_fixture("transparencia_documento_pf"))
            return httpx.Response(200, content=b"")
        if "/contratos/cpf-cnpj" in url:
            return httpx.Response(200, json=carrega_fixture("transparencia_contratos_cnpj"))
        if "/pessoa-juridica" in url:
            return httpx.Response(200, json=carrega_fixture("transparencia_pessoa_juridica"))
        if "/emendas" in url:
            return httpx.Response(200, json=carrega_fixture("transparencia_emendas"))
        if "/ceis" in url:
            return httpx.Response(200, json=carrega_fixture("transparencia_ceis"))
        if "/cnep" in url:
            return httpx.Response(200, json=carrega_fixture("transparencia_cnep"))
        if "novo-bolsa-familia-por-municipio" in url:
            return httpx.Response(200, json=carrega_fixture("transparencia_bolsa"))
    # ANP — CSV rolante de preços de combustível; o firewall real barra UA
    # técnico (403) e Accept: application/json (401) — o mock protege os dois
    if "gov.br/anp" in url and "ultimas-4-semanas" in url:
        if "Mozilla" not in request.headers.get("user-agent", ""):
            return httpx.Response(403, text="Forbidden")
        if request.headers.get("accept") == "application/json":
            return httpx.Response(401, text="Unauthorized")
        return httpx.Response(
            200, text=(FIXTURES / "anp_precos.csv").read_text(encoding="utf-8")
        )
    # Tesouro Direto — CSV de 14 MB sem ordem cronológica (fixture encolhida)
    if "tesourotransparente.gov.br" in url and "precotaxatesourodireto" in url:
        return httpx.Response(
            200, text=(FIXTURES / "tesourodireto.csv").read_text(encoding="utf-8")
        )
    # DataJud (CNJ) — Elasticsearch por tribunal; agregação vs busca pelo corpo
    if "api-publica.datajud.cnj.jus.br" in url:
        if not request.headers.get("authorization", "").startswith("APIKey "):
            return httpx.Response(401, json={"error": "missing api key"})
        corpo = json.loads(request.content or b"{}")
        if "aggs" in corpo:
            return httpx.Response(200, json=carrega_fixture("datajud_resumo"))
        return httpx.Response(200, json=carrega_fixture("datajud_processos"))
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
    # Senado (API nova de processos): matérias legislativas
    if "/dadosabertos/processo" in url:
        return httpx.Response(200, json=carrega_fixture("senado_processos"))
    # TSE — ZIP da prestação de contas (o conector baixa por streaming)
    if "cdn.tse.jus.br" in url and "prestacao_de_contas" in url:
        return httpx.Response(200, content=(FIXTURES / "tse_doacoes.zip").read_bytes())
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
    app.state.siconv = ArquivosSiconv(cliente_fake)
    # o cache em disco do TSE vai pra uma pasta so desta suite, pra nao
    # colidir com um zip real baixado fora dos testes
    app.state.connectors["tse"].pasta = Path(tempfile.mkdtemp(prefix="balcao-tse-teste-"))
    return app, cliente_fake


@pytest.fixture
async def api():
    app, cliente_fake = monta_app()
    transporte = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transporte, base_url="http://teste") as cliente:
        yield cliente
    await cliente_fake.aclose()
