"""A rota cross-fonte /v1/arrecadacao: resolve o ente (brasil, UF, código IBGE
ou nome de cidade) e junta panorama + impostos + despesa num pacote só."""


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
