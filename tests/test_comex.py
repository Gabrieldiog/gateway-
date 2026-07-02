async def test_balanca_junta_os_fluxos_e_calcula_o_saldo(api):
    resp = await api.get("/v1/comex/balanca?de=2026-01&ate=2026-05")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["meta"]["fonte"]["nome"].startswith("ComexStat")
    assert corpo["meta"]["moeda"] == "US$ FOB"
    # meses saem em ordem cronológica
    assert [b["mes"] for b in corpo["dados"]] == ["2026-04", "2026-05"]
    maio = corpo["dados"][1]
    assert float(maio["exportacoes"]) == 31904049589
    assert float(maio["importacoes"]) == 31904049589 // 2
    assert float(maio["saldo"]) == 31904049589 - 31904049589 // 2


async def test_ranking_por_pais(api):
    resp = await api.get("/v1/comex/ranking/pais")
    assert resp.status_code == 200
    corpo = resp.json()
    top = corpo["dados"][0]
    assert top["nome"] == "China"
    assert top["dimensao"] == "pais"
    assert top["fluxo"] == "exportacao"
    # a métrica string da fonte vira número de verdade
    assert float(top["valor_fob"]) == 46263322664


async def test_ranking_por_uf_e_produto(api):
    uf = (await api.get("/v1/comex/ranking/uf")).json()["dados"][0]
    assert uf["nome"] == "São Paulo"
    produto = (await api.get("/v1/comex/ranking/produto")).json()["dados"][0]
    assert produto["codigo"] == "27"
    assert "Combustíveis" in produto["nome"]


async def test_solucos_do_mdic_sao_retentados():
    # o MDIC responde 200 com success=false de vez em quando; sem a nova
    # tentativa, o primeiro acesso com cache frio virava 502 na cara
    import httpx
    from httpx import MockTransport

    from balcao.connectors.comex import ComexConnector

    contagem = {"chamadas": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        contagem["chamadas"] += 1
        if contagem["chamadas"] == 1:
            return httpx.Response(200, json={"success": False, "data": None})
        return httpx.Response(
            200,
            json={"success": True, "data": {"list": [
                {"year": "2026", "country": "China", "metricFOB": "1", "metricKG": "1"}
            ]}},
        )

    cliente = httpx.AsyncClient(transport=MockTransport(handler))
    conector = ComexConnector(cliente, retry_tentativas=1)
    resposta = await conector.fetch("ranking/pais")
    assert resposta.total == 1
    assert contagem["chamadas"] == 2
    await cliente.aclose()


async def test_fluxo_invalido_da_400(api):
    resp = await api.get("/v1/comex/ranking/pais?fluxo=contrabando")
    assert resp.status_code == 400


async def test_mes_invalido_da_400(api):
    resp = await api.get("/v1/comex/balanca?de=janeiro")
    assert resp.status_code == 400
