"""Expõe o núcleo do Balcão como ferramentas MCP (FastMCP): um agente de IA
consulta dados públicos brasileiros pelas mesmas fontes do gateway HTTP.

Rodar:  python -m balcao.mcp_server   (stdio, pra plugar no Claude/IDE)
"""

from fastmcp import FastMCP

from balcao import connectors  # noqa: F401  o import registra as fontes
from balcao.config import get_settings
from balcao.connectors.base import BaseConnector, connector_classes
from balcao.http import cria_client
from balcao.resilience import CircuitBreaker
from balcao.search import busca_unificada, gastos_deputado

mcp = FastMCP(
    "Balcão",
    instructions=(
        "Gateway de dados públicos brasileiros. Use as ferramentas para "
        "consultar deputados e gastos da Câmara, senadores, séries econômicas "
        "do Banco Central (selic, ipca, dólar) e municípios/estados do IBGE, "
        "ou 'buscar' para procurar um termo em várias fontes de uma vez."
    ),
)

# os conectores são montados sob demanda; testes injetam os seus via
# configura_conectores() pra rodar sem tocar a rede.
_conectores: dict[str, BaseConnector] | None = None


def configura_conectores(conectores: dict[str, BaseConnector]) -> None:
    global _conectores
    _conectores = conectores


def _get() -> dict[str, BaseConnector]:
    global _conectores
    if _conectores is None:
        s = get_settings()
        client = cria_client(s)
        _conectores = {
            nome: cls(
                client,
                retry_tentativas=s.retry_tentativas,
                breaker=CircuitBreaker(s.breaker_falhas, s.breaker_cooldown),
            )
            for nome, cls in connector_classes().items()
        }
    return _conectores


@mcp.tool
async def listar_fontes() -> list[dict]:
    """Lista as fontes disponíveis e os recursos de cada uma."""
    return [
        {"nome": c.name, "descricao": c.description, "recursos": list(c.resources)}
        for c in _get().values()
    ]


@mcp.tool
async def buscar(termo: str, fontes: list[str] | None = None) -> dict:
    """Busca um termo em várias fontes em paralelo e junta o resultado.
    Sem `fontes`, procura em todas. Erro numa fonte não derruba as outras."""
    return await busca_unificada(_get(), termo, fontes)


@mcp.tool
async def deputados(uf: str | None = None, partido: str | None = None) -> list[dict]:
    """Lista deputados federais em exercício, filtrando por UF e/ou partido."""
    params: dict = {}
    if uf:
        params["uf"] = uf
    if partido:
        params["partido"] = partido
    return (await _get()["camara"].fetch("deputados", **params)).dados


@mcp.tool
async def gastos(deputado: str, ano: int = 2024) -> dict:
    """Cota parlamentar (CEAP) de um deputado, por id ou nome, agregada por tipo."""
    return await gastos_deputado(_get()["camara"], deputado, ano)


@mcp.tool
async def senadores(uf: str | None = None, partido: str | None = None) -> list[dict]:
    """Lista senadores em exercício, filtrando por UF e/ou partido."""
    params: dict = {}
    if uf:
        params["uf"] = uf
    if partido:
        params["partido"] = partido
    return (await _get()["senado"].fetch("senadores", **params)).dados


@mcp.tool
async def serie_economica(serie: str, ultimos: int = 12) -> list[dict]:
    """Série do Banco Central por apelido (selic, cdi, ipca, igpm, dolar, euro)
    ou por código numérico do SGS."""
    recurso = f"serie/{serie}" if serie.isdigit() else serie
    return (await _get()["bacen"].fetch(recurso, ultimos=str(ultimos))).dados


@mcp.tool
async def municipios(uf: str) -> list[dict]:
    """Municípios de uma UF (ex.: SP)."""
    return (await _get()["ibge"].fetch("municipios", uf=uf)).dados


if __name__ == "__main__":
    mcp.run()
