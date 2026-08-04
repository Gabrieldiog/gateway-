from decimal import Decimal


async def test_panorama_estado(api):
    resp = await api.get("/v1/tesouro/estados/SP?ano=2021")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["total"] == 1
    fin = corpo["dados"][0]
    assert fin["nivel"] == "estado"
    assert fin["ente"] == "SP"
    assert fin["uf"] == "SP"
    assert fin["receita_total"] == "305164395104.99"
    assert fin["receita_impostos"] == "220013879151.03"
    assert fin["despesa_total"] == "272678508647.89"
    assert fin["populacao"] == 44000000


async def test_panorama_uniao(api):
    resp = await api.get("/v1/tesouro/uniao?ano=2023")
    assert resp.status_code == 200
    fin = resp.json()["dados"][0]
    assert fin["nivel"] == "uniao"
    assert fin["ente"] == "Brasil"
    assert fin["uf"] is None
    assert fin["receita_total"] == "4483657519633.49"
    assert fin["receita_impostos"] == "931028666487.66"
    assert fin["despesa_total"] == "4564283084454.05"


async def test_arrecadacao_total_inclui_contribuicoes(api):
    resp = await api.get("/v1/tesouro/uniao?ano=2023")
    fin = resp.json()["dados"][0]
    # arrecadação total = impostos+taxas (1.1) + contribuições (1.2)
    assert Decimal(fin["receita_contribuicoes"]) == Decimal("1221000000000")
    assert Decimal(fin["arrecadacao_total"]) == Decimal("940000000000") + Decimal("1221000000000")
    # e é bem maior que só impostos; é a diferença que confunde quem compara
    assert Decimal(fin["arrecadacao_total"]) > Decimal(fin["receita_impostos"])


async def test_panorama_municipio(api):
    resp = await api.get("/v1/tesouro/municipios/5208707?ano=2023")
    assert resp.status_code == 200
    fin = resp.json()["dados"][0]
    assert fin["nivel"] == "municipio"
    # o nome sai do campo "instituicao" do próprio DCA, limpo do prefixo e da UF
    assert fin["ente"] == "Goiânia"
    assert fin["uf"] == "GO"
    assert fin["ibge"] == 5208707
    assert fin["receita_impostos"] == "3043090527.89"
    assert fin["populacao"] == 1555626


async def test_despesa_municipio(api):
    resp = await api.get("/v1/tesouro/municipios/5208707/despesas?ano=2023")
    assert resp.status_code == 200
    dados = resp.json()["dados"]
    assert dados[0]["ente"] == "Goiânia"
    assert dados[0]["nivel"] == "municipio"
    assert [d["funcao"] for d in dados] == ["Saúde", "Educação", "Urbanismo"]


async def test_municipio_ibge_invalido_da_400(api):
    resp = await api.get("/v1/tesouro/municipios/123")
    assert resp.status_code == 400


async def test_impostos_uniao(api):
    resp = await api.get("/v1/tesouro/uniao/impostos?ano=2023")
    assert resp.status_code == 200
    corpo = resp.json()
    siglas = [d["sigla"] for d in corpo["dados"]]
    assert siglas[0] == "IR"  # o maior imposto federal
    assert set(siglas) >= {"IR", "IPI", "IOF", "II", "IE", "ITR"}
    assert "OUTROS" not in siglas  # a soma já fecha sem sobra
    assert corpo["dados"][0]["nivel"] == "uniao"
    assert corpo["dados"][0]["ente"] == "Brasil"
    assert corpo["meta"]["total_impostos"] == "931028666487.66"


async def test_impostos_municipio(api):
    resp = await api.get("/v1/tesouro/municipios/5208707/impostos?ano=2023")
    assert resp.status_code == 200
    corpo = resp.json()
    impostos = {d["sigla"]: Decimal(d["valor"]) for d in corpo["dados"]}
    assert set(impostos) == {"ISS", "IPTU", "ITBI", "IR"}
    assert impostos["ISS"] > impostos["IPTU"]
    assert corpo["dados"][0]["ente"] == "Goiânia"
    # a quebra fecha com o total de impostos do ente
    assert sum(impostos.values()) == Decimal(corpo["meta"]["total_impostos"])


async def test_impostos_estado_com_residual(api):
    resp = await api.get("/v1/tesouro/estados/SP/impostos?ano=2021")
    assert resp.status_code == 200
    corpo = resp.json()
    impostos = {d["sigla"]: Decimal(d["valor"]) for d in corpo["dados"]}
    assert impostos["ICMS"] == Decimal("180000000000.00")
    assert "IPVA" in impostos and "ITCMD" in impostos
    # o que não caiu num imposto nomeado vira "Outros" pra soma sempre fechar
    assert "OUTROS" in impostos
    assert sum(impostos.values()) == Decimal(corpo["meta"]["total_impostos"])


async def test_despesa_por_funcao_ordenada(api):
    resp = await api.get("/v1/tesouro/estados/SP/despesas?ano=2021")
    assert resp.status_code == 200
    dados = resp.json()["dados"]
    # só funções de 1º nível, ordenadas por valor desc; subfunção e coluna
    # liquidada ficam de fora
    assert [d["funcao"] for d in dados] == ["Educação", "Saúde", "Segurança Pública"]
    assert Decimal(dados[0]["valor"]) == Decimal("40000000000")


async def test_uf_invalida_da_400(api):
    resp = await api.get("/v1/tesouro/estados/XX")
    assert resp.status_code == 400


async def test_tesouro_aparece_em_fontes(api):
    resp = await api.get("/v1/fontes")
    nomes = {f["nome"] for f in resp.json()["fontes"]}
    assert "tesouro" in nomes
