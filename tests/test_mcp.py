import httpx
from fastmcp import Client
from httpx import MockTransport

from balcao import mcp_server
from balcao.connectors.base import connector_classes

from conftest import responde_fake


def conectores_fake():
    cliente = httpx.AsyncClient(transport=MockTransport(responde_fake))
    conectores = {n: cls(cliente) for n, cls in connector_classes().items()}
    mcp_server.configura_conectores(conectores)
    return cliente


async def test_mcp_lista_as_ferramentas():
    cliente = conectores_fake()
    try:
        async with Client(mcp_server.mcp) as c:
            nomes = {t.name for t in await c.list_tools()}
        assert {
            "buscar",
            "deputados",
            "gastos",
            "senadores",
            "serie_economica",
            "municipios",
            "listar_fontes",
        } <= nomes
    finally:
        await cliente.aclose()


async def test_mcp_buscar_junta_fontes():
    cliente = conectores_fake()
    try:
        async with Client(mcp_server.mcp) as c:
            r = await c.call_tool("buscar", {"termo": "alan", "fontes": ["camara", "senado"]})
        dados = r.data
        assert dados["total"] > 0
        assert dados["erros"] == {}
        tipos = {x["tipo_resultado"] for x in dados["resultados"]}
        assert "deputado" in tipos or "senador" in tipos
    finally:
        await cliente.aclose()


async def test_mcp_serie_economica():
    cliente = conectores_fake()
    try:
        async with Client(mcp_server.mcp) as c:
            r = await c.call_tool("serie_economica", {"serie": "selic", "ultimos": 5})
        assert isinstance(r.data, list) and r.data
        assert r.data[0]["serie"] == 432
    finally:
        await cliente.aclose()


async def test_mcp_gastos_agrega():
    cliente = conectores_fake()
    try:
        async with Client(mcp_server.mcp) as c:
            r = await c.call_tool("gastos", {"deputado": "204528", "ano": 2025})
        assert r.data["valor_total"] == "730.5"
        assert r.data["total_documentos"] == 3
    finally:
        await cliente.aclose()
