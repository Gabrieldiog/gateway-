import httpx
import pytest
from httpx import MockTransport

from balcao.connectors.transparencia import TransparenciaConnector
from balcao.exceptions import ChaveFaltando


async def test_emendas_normaliza_o_valor_brasileiro(api):
    resp = await api.get("/v1/transparencia/emendas?ano=2025")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["meta"]["fonte"]["nome"].startswith("Portal da Transparência")
    bancada = next(e for e in corpo["dados"] if e["tipo"] == "Emenda de Bancada")
    # "1.500.000,50" na fonte vira Decimal de verdade aqui
    assert bancada["valor_empenhado"] == "1500000.50"
    assert bancada["valor_liquidado"] == "750000.25"
    assert bancada["funcao"] == "Saúde"


async def test_sancoes_junta_ceis_e_cnep(api):
    resp = await api.get("/v1/transparencia/sancoes?documento=12.345.678/0001-90")
    assert resp.status_code == 200
    corpo = resp.json()
    cadastros = {s["cadastro"] for s in corpo["dados"]}
    assert cadastros == {"CEIS", "CNEP"}
    ceis = next(s for s in corpo["dados"] if s["cadastro"] == "CEIS")
    assert ceis["sancionado"] == "EMPRESA EXEMPLO LTDA"
    # data dd/mm/aaaa da fonte sai ISO
    assert ceis["inicio"] == "2022-09-20"
    assert ceis["esfera"] == "ESTADUAL"
    # o documento com máscara foi limpo pra consulta
    assert corpo["meta"]["documento"] == "12345678000190"


async def test_sancoes_sem_documento_da_400(api):
    resp = await api.get("/v1/transparencia/sancoes")
    assert resp.status_code == 400


async def test_bolsa_familia_por_municipio(api):
    resp = await api.get("/v1/transparencia/bolsa-familia?municipio=3550308&mes=202605")
    assert resp.status_code == 200
    b = resp.json()["dados"][0]
    assert b["municipio"] == "SÃO PAULO"
    assert b["uf"] == "SP"
    assert b["beneficiarios"] == 611753
    assert float(b["valor"]) == 406295426.0


async def test_bolsa_familia_mes_invalido_da_400(api):
    resp = await api.get("/v1/transparencia/bolsa-familia?municipio=3550308&mes=maio")
    assert resp.status_code == 400


async def test_sem_chave_da_erro_limpo():
    cliente = httpx.AsyncClient(
        transport=MockTransport(lambda r: httpx.Response(200, json=[]))
    )
    conector = TransparenciaConnector(cliente, chave="")
    with pytest.raises(ChaveFaltando) as exc:
        await conector.fetch("emendas")
    assert exc.value.status_code == 503
    assert "TRANSPARENCIA_API_KEY" in exc.value.mensagem
    await cliente.aclose()
