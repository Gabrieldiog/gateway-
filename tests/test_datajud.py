import httpx
import pytest
from httpx import MockTransport

from balcao.connectors.datajud import DatajudConnector
from balcao.exceptions import ChaveFaltando


async def test_processo_por_numero_normalizado(api):
    resp = await api.get("/v1/datajud/processos/tjgo?numero=5058703-19.2021.8.09.0051")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["meta"]["fonte"]["nome"].startswith("DataJud")
    # o número com máscara foi limpo pra consulta
    assert corpo["meta"]["numero"] == "50587031920218090051"
    p = corpo["dados"][0]
    assert p["classe"] == "Cumprimento de Sentença de Ações Coletivas"
    assert p["orgao"] == "8ª Vara da Fazenda Pública Estadual"
    assert p["assuntos"] == ["Obrigação de Fazer / Não Fazer"]
    assert p["ajuizado_em"] == "2021-08-11"
    assert p["movimentos"] == 2
    # o último andamento é o de dataHora mais recente, não o último da lista
    assert p["ultimo_movimento"] == "Conclusão para despacho"
    assert p["ultimo_movimento_em"] == "2026-06-19"


async def test_resumo_traz_as_classes_mais_comuns(api):
    resp = await api.get("/v1/datajud/resumo/tjgo")
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["meta"]["total_processos"] == 5000000
    top = corpo["dados"][0]
    assert top["classe"] == "Execução Fiscal"
    assert top["processos"] == 847454


async def test_tribunal_invalido_da_400(api):
    resp = await api.get("/v1/datajud/processos/tj%20go")
    assert resp.status_code == 400


async def test_sem_chave_da_erro_limpo():
    cliente = httpx.AsyncClient(
        transport=MockTransport(lambda r: httpx.Response(200, json={}))
    )
    conector = DatajudConnector(cliente, chave="")
    with pytest.raises(ChaveFaltando) as exc:
        await conector.fetch("resumo/tjgo")
    assert "DATAJUD_API_KEY" in exc.value.mensagem
    await cliente.aclose()
