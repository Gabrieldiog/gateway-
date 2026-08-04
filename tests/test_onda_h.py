"""Onda H, a API pública: referência Scalar, rate limit por chave, headers."""

from starlette.requests import Request

from balcao.ratelimit import cria_limiter, extrai_chave, le_chaves


def faz_request(headers=None, query: str = "") -> Request:
    return Request({
        "type": "http", "method": "GET", "path": "/",
        "headers": [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()],
        "query_string": query.encode(),
        "client": ("203.0.113.7", 12345),
    })


def test_le_chaves_separa_csv_e_ignora_vazio():
    assert le_chaves("a, b ,,c") == {"a", "b", "c"}
    assert le_chaves("") == set()


def test_extrai_chave_do_header_ou_da_query():
    assert extrai_chave(faz_request(headers={"x-api-key": "abc"})) == "abc"
    assert extrai_chave(faz_request(query="chave=xyz")) == "xyz"
    assert extrai_chave(faz_request()) is None


def test_balde_isola_chave_valida_do_ip():
    limiter = cria_limiter("100/minute", {"boa"})
    balde = limiter._key_func
    # chave válida -> balde próprio; inválida ou ausente -> balde do IP
    assert balde(faz_request(headers={"x-api-key": "boa"})) == "chave:boa"
    assert balde(faz_request(headers={"x-api-key": "falsa"})).startswith("ip:")
    assert balde(faz_request()).startswith("ip:")


async def test_scalar_serve_a_referencia(api):
    resp = await api.get("/scalar")
    assert resp.status_code == 200
    assert "api-reference" in resp.text
    assert "/openapi.json" in resp.text


async def test_openapi_lista_as_rotas(api):
    resp = await api.get("/openapi.json")
    assert resp.status_code == 200
    caminhos = resp.json()["paths"]
    assert "/v1/fontes" in caminhos
    # as fontes passam pela rota genérica passthrough
    assert "/v1/{fonte}/{recurso}" in caminhos


async def test_resposta_traz_headers_de_rate_limit(api):
    resp = await api.get("/health")
    assert resp.headers.get("x-ratelimit-limit") is not None
    # cabeçalhos de segurança pra exposição pública
    assert resp.headers.get("x-content-type-options") == "nosniff"
