async def test_panorama_estado(api):
    resp = await api.get("/v1/tesouro/estados/SP?ano=2021")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["total"] == 1
    fin = corpo["dados"][0]
    assert fin["uf"] == "SP"
    assert fin["receita_total"] == "305164395104.99"
    assert fin["receita_impostos"] == "220013879151.03"
    assert fin["despesa_total"] == "272678508647.89"
    assert fin["populacao"] == 44000000


async def test_despesa_por_funcao_ordenada(api):
    from decimal import Decimal

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
