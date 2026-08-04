"""Cotações em tempo real. Fonte tempo-real: passa por um cache CURTO
(cache_vivo_ttl), fresco de segundos mas sem martelar a AwesomeAPI, que
rate-limita (429) um IP fixo consultando a cada request.

A AwesomeAPI é o caminho feliz; como ela cobra cadastro e barra IP de
datacenter, o conector tem plano B em fontes abertas. Os testes daqui pra
baixo cobrem os dois caminhos e a honestidade sobre qual serviu o dado."""


async def test_cotacoes_last(api):
    resp = await api.get("/v1/cotacoes/last/USD-BRL,EUR-BRL,BTC-BRL")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["total"] == 3
    por_moeda = {c["moeda"]: c for c in corpo["dados"]}
    dolar = por_moeda["USD"]
    assert dolar["par"] == "USD/BRL"
    assert dolar["compra"] == "5.1796"
    assert dolar["venda"] == "5.1806"
    assert dolar["variacao_pct"] == -0.15
    assert dolar["atualizado"] == "2026-06-30 16:53:26"


async def test_cotacoes_par_invalido_da_400(api):
    resp = await api.get("/v1/cotacoes/last/DOLAR")
    assert resp.status_code == 400


async def test_cotacoes_cache_curto(api):
    # fonte tempo-real: a 1ª chamada busca fresco (miss), a 2ª idêntica volta
    # do cache curto (hit); é o que segura o rate limit da AwesomeAPI sem
    # perder o frescor de segundos
    primeira = await api.get("/v1/cotacoes/last/USD-BRL")
    segunda = await api.get("/v1/cotacoes/last/USD-BRL")
    assert segunda.status_code == 200
    assert primeira.json()["meta"].get("cache") is None
    assert segunda.json()["meta"].get("cache") == "hit"


async def test_cotacoes_aparece_em_fontes(api):
    resp = await api.get("/v1/fontes")
    nomes = {f["nome"] for f in resp.json()["fontes"]}
    assert "cotacoes" in nomes


# --- plano B: as fontes sem cadastro ------------------------------------
# O /pulso vivia caindo porque dependia de uma fonte so, comercial, que barra
# IP de datacenter. Sem token o conector respondia 503 "falta chave" e o
# caderno inteiro morria. Agora o token e so um atalho: faltando ele ou
# levando 429, o gateway serve o mesmo dado por fontes abertas.


async def test_cotacoes_sem_token_nao_da_503(api, sem_awesomeapi_token):
    # o bug relatado: servidor sem AWESOMEAPI_TOKEN devolvia 503 e o caderno
    # Pulso mostrava "falta uma chave no servidor"
    resp = await api.get("/v1/cotacoes/last/USD-BRL")
    assert resp.status_code == 200
    assert "USD" in {c["moeda"] for c in resp.json()["dados"]}


async def test_cotacoes_nao_exige_mais_chave(api):
    resp = await api.get("/v1/fontes")
    cotacoes = next(f for f in resp.json()["fontes"] if f["nome"] == "cotacoes")
    assert cotacoes["precisa_chave"] is False


async def test_plano_b_serve_cambio_ouro_e_cripto(api_awesomeapi_fora):
    # AwesomeAPI barrada (429): o caderno continua de pe pelas fontes abertas
    resp = await api_awesomeapi_fora.get("/v1/cotacoes/last/USD-BRL,XAU-BRL,BTC-BRL")
    assert resp.status_code == 200
    por_moeda = {c["moeda"]: c for c in resp.json()["dados"]}
    assert set(por_moeda) == {"USD", "XAU", "BTC"}

    # cambio: 1 BRL = 0,19733 USD na fixture, entao USD/BRL = 1/0,19733
    assert round(float(por_moeda["USD"]["compra"]), 4) == 5.0677
    # ouro: 4053.800049 USD a onca, convertido pelo mesmo dolar
    assert round(float(por_moeda["XAU"]["compra"])) == 20543
    # cripto: preco ja vem em real na exchange brasileira
    assert float(por_moeda["BTC"]["compra"]) == 324100.0


async def test_plano_b_diz_de_onde_veio_cada_numero(api_awesomeapi_fora):
    # o projeto inteiro se apoia em dizer a fonte; trocar de fonte calado
    # seria pior que o erro
    resp = await api_awesomeapi_fora.get("/v1/cotacoes/last/USD-BRL,XAU-BRL,BTC-BRL")
    corpo = resp.json()
    por_moeda = {c["moeda"]: c for c in corpo["dados"]}
    assert por_moeda["USD"]["origem"] == "frankfurter"
    assert por_moeda["XAU"]["origem"] == "gold-api"
    assert por_moeda["BTC"]["origem"] == "mercadobitcoin"
    assert corpo["meta"]["plano_b"] is True
    assert set(corpo["meta"]["origens"]) == {"frankfurter", "gold-api", "mercadobitcoin"}


async def test_plano_b_nao_finge_tempo_real_no_cambio(api_awesomeapi_fora):
    # o Frankfurter publica a taxa de referencia do BCE uma vez por dia; o
    # selo "ao vivo" mentiria. Cripto e ouro seguem sendo de agora.
    resp = await api_awesomeapi_fora.get("/v1/cotacoes/last/USD-BRL,XAU-BRL,BTC-BRL")
    por_moeda = {c["moeda"]: c for c in resp.json()["dados"]}
    assert por_moeda["USD"]["ao_vivo"] is False
    assert por_moeda["XAU"]["ao_vivo"] is True
    assert por_moeda["BTC"]["ao_vivo"] is True


async def test_plano_b_calcula_variacao_do_cambio(api_awesomeapi_fora):
    # de 0,19769 pra 0,19733 USD por real o dolar SUBIU: a variacao e do par,
    # nao da taxa invertida que a fonte devolve
    resp = await api_awesomeapi_fora.get("/v1/cotacoes/last/USD-BRL")
    dolar = resp.json()["dados"][0]
    assert dolar["variacao_pct"] == 0.18


async def test_awesomeapi_ganha_quando_responde(api):
    # o plano B e rede de seguranca, nao substituto: com a AwesomeAPI de pe o
    # dado continua vindo dela (tempo real de verdade)
    resp = await api.get("/v1/cotacoes/last/USD-BRL")
    corpo = resp.json()
    assert corpo["dados"][0]["origem"] == "awesomeapi"
    assert corpo["meta"].get("plano_b") is False


async def test_par_sem_cobertura_no_plano_b_nao_derruba_o_resto(api_awesomeapi_fora):
    # ZZZ nao existe em fonte nenhuma; o caderno ainda mostra o dolar
    resp = await api_awesomeapi_fora.get("/v1/cotacoes/last/USD-BRL,ZZZ-BRL")
    assert resp.status_code == 200
    assert [c["moeda"] for c in resp.json()["dados"]] == ["USD"]


async def test_cripto_sobrevive_ao_bloqueio_da_binance(api_como_no_render):
    # o que aconteceu no deploy: a Binance responde 451 pra IP dos EUA (regiao
    # padrao do Render) e a secao de cripto do Pulso sumia inteira, calada
    resp = await api_como_no_render.get("/v1/cotacoes/last/USD-BRL,BTC-BRL,ETH-BRL")
    assert resp.status_code == 200
    por_moeda = {c["moeda"]: c for c in resp.json()["dados"]}
    assert set(por_moeda) == {"USD", "BTC", "ETH"}
    assert por_moeda["BTC"]["origem"] == "mercadobitcoin"
    assert float(por_moeda["BTC"]["compra"]) == 324100.0


async def test_mercado_bitcoin_calcula_variacao_do_dia(api_como_no_render):
    # a fonte da abertura e o ultimo preco; a variacao sai dai
    resp = await api_como_no_render.get("/v1/cotacoes/last/BTC-BRL")
    # de 323368 pra 324100
    assert resp.json()["dados"][0]["variacao_pct"] == 0.23


async def test_cripto_cai_pra_binance_se_o_mercado_bitcoin_faltar(api_sem_mercado_bitcoin):
    # duas fontes de cripto, nao uma: a brasileira primeiro, a global atras
    resp = await api_sem_mercado_bitcoin.get("/v1/cotacoes/last/BTC-BRL")
    assert resp.status_code == 200
    assert resp.json()["dados"][0]["origem"] == "binance"


async def test_meta_denuncia_o_par_que_ninguem_serviu(api_como_no_render):
    # some uma secao da tela sem ninguem avisar foi exatamente o bug; agora a
    # resposta diz quais pares ficaram sem fonte
    resp = await api_como_no_render.get("/v1/cotacoes/last/USD-BRL,ZZZ-BRL")
    assert resp.status_code == 200
    assert resp.json()["meta"]["sem_fonte"] == ["ZZZ/BRL"]


async def test_meta_nao_inventa_falta_quando_veio_tudo(api_como_no_render):
    resp = await api_como_no_render.get("/v1/cotacoes/last/USD-BRL,BTC-BRL")
    assert resp.json()["meta"]["sem_fonte"] == []


async def test_plano_b_tambem_falhando_vira_502(api_awesomeapi_fora):
    # sem nenhuma fonte de pe, o honesto e dizer que a fonte caiu (502), nao
    # devolver lista vazia como se nao houvesse cotacao no mundo
    resp = await api_awesomeapi_fora.get("/v1/cotacoes/last/ZZZ-BRL")
    assert resp.status_code == 502
