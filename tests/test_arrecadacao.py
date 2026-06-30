"""A rota cross-fonte /v1/arrecadacao: resolve o ente (brasil, UF, código IBGE
ou nome de cidade) e junta panorama + impostos + despesa num pacote só."""

from decimal import Decimal


async def test_arrecadacao_brasil(api):
    resp = await api.get("/v1/arrecadacao?ente=brasil&ano=2023")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["ente"]["nivel"] == "uniao"
    assert corpo["ente"]["ente"] == "Brasil"
    assert "IR" in [i["sigla"] for i in corpo["impostos"]]
    assert corpo["total_impostos"] == "931028666487.66"
    assert corpo["despesas"]  # juntou a despesa por função


async def test_arrecadacao_por_uf(api):
    resp = await api.get("/v1/arrecadacao?ente=SP&ano=2023")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["ente"]["nivel"] == "estado"
    assert "ICMS" in [i["sigla"] for i in corpo["impostos"]]


async def test_arrecadacao_por_codigo_ibge(api):
    resp = await api.get("/v1/arrecadacao?ente=5208707&ano=2023")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["ente"]["nivel"] == "municipio"
    assert corpo["ente"]["ente"] == "Goiânia"
    assert "ISS" in [i["sigla"] for i in corpo["impostos"]]
    assert corpo["despesas"]


async def test_arrecadacao_resolve_cidade_por_nome(api):
    # 'adamantina' é resolvido pelo IBGE (id 3500105) e consultado no Tesouro
    resp = await api.get("/v1/arrecadacao?ente=adamantina&ano=2023")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["ente"]["nivel"] == "municipio"
    assert "ISS" in [i["sigla"] for i in corpo["impostos"]]


async def test_arrecadacao_cidade_inexistente_da_404(api):
    resp = await api.get("/v1/arrecadacao?ente=narnia&ano=2023")
    assert resp.status_code == 404


async def test_arrecadacao_cacheia(api):
    primeira = await api.get("/v1/arrecadacao?ente=brasil&ano=2023")
    segunda = await api.get("/v1/arrecadacao?ente=brasil&ano=2023")
    assert segunda.status_code == 200
    assert segunda.json() == primeira.json()


# --- /v1/arrecadacao/ranking: varre os 27 estados ou as 27 capitais ---


async def test_ranking_estados_por_total(api):
    resp = await api.get("/v1/arrecadacao/ranking?nivel=estado")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["nivel"] == "estado"
    assert corpo["por"] == "total"
    assert corpo["imposto"] is None
    assert corpo["total_entes"] == 27
    assert len(corpo["ranking"]) == 27
    # ranqueia pelo total de impostos do ente
    assert corpo["ranking"][0]["valor"] == "220013879151.03"


async def test_ranking_estados_por_imposto(api):
    resp = await api.get("/v1/arrecadacao/ranking?nivel=estado&imposto=ICMS")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["imposto"] == "ICMS"
    assert Decimal(corpo["ranking"][0]["valor"]) == Decimal("180000000000")


async def test_ranking_capitais_por_iss(api):
    resp = await api.get("/v1/arrecadacao/ranking?nivel=capital&imposto=ISS")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["total_entes"] == 27
    linha = corpo["ranking"][0]
    assert linha["ente"] == "Goiânia"  # fixture de município
    assert linha["valor"] == "1183301002.96"


async def test_ranking_per_capita(api):
    resp = await api.get("/v1/arrecadacao/ranking?nivel=estado&por=per_capita")
    assert resp.status_code == 200
    linha = resp.json()["ranking"][0]
    esperado = Decimal(linha["total_impostos"]) / linha["populacao"]
    assert Decimal(linha["valor"]) == esperado


async def test_ranking_limit(api):
    resp = await api.get("/v1/arrecadacao/ranking?nivel=estado&limit=5")
    assert resp.status_code == 200
    assert len(resp.json()["ranking"]) == 5


async def test_ranking_nivel_invalido_da_422(api):
    resp = await api.get("/v1/arrecadacao/ranking?nivel=municipio")
    assert resp.status_code == 422
