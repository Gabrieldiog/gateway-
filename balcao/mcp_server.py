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
from balcao.search import arrecadacao_ente, busca_unificada, gastos_deputado

mcp = FastMCP(
    "Balcão",
    instructions=(
        "Gateway de dados públicos brasileiros com 25 fontes normalizadas: "
        "Congresso (deputados, gastos, votos, matérias), economia (BACEN, Focus, "
        "IPEADATA, B3, câmbio), dinheiro público (arrecadação, emendas, sanções, "
        "Bolsa Família, licitações), tempo real (energia do ONS, queimadas do "
        "INPE), preços (combustíveis da ANP, Tesouro Direto), comércio exterior, "
        "dengue, processos judiciais e doações de campanha. Comece com "
        "'listar_fontes' pra ver o catálogo e use 'consultar' pra qualquer "
        "recurso; as demais ferramentas são atalhos das perguntas mais comuns."
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


@mcp.tool
async def consultar(fonte: str, recurso: str, params: dict | None = None) -> dict:
    """Consulta QUALQUER recurso de qualquer fonte do Balcão, o passe livre.
    Use 'listar_fontes' pra ver os nomes e recursos (ex.: fonte='anp',
    recurso='precos', params={'combustivel': 'gasolina'})."""
    conectores = _get()
    if fonte not in conectores:
        return {"erro": f"fonte desconhecida: {fonte!r}", "disponiveis": sorted(conectores)}
    resposta = await conectores[fonte].fetch(recurso, **(params or {}))
    return resposta.model_dump(mode="json")


@mcp.tool
async def arrecadacao(ente: str = "brasil", ano: int = 2024) -> dict:
    """Quanto um ente arrecadou e gastou: 'brasil', uma UF (GO) ou uma cidade
    (nome ou código IBGE). Impostos por tipo e despesas por função."""
    conectores = _get()
    return await arrecadacao_ente(conectores["tesouro"], conectores["ibge"], ente, ano, None)


@mcp.tool
async def energia_agora() -> list[dict]:
    """A geração de energia do Brasil neste minuto: mix por fonte (hidráulica,
    eólica, solar, térmica, nuclear), carga e % renovável, pelo ONS."""
    return (await _get()["ons"].fetch("geracao")).dados


@mcp.tool
async def preco_combustivel(combustivel: str = "gasolina", uf: str | None = None) -> list[dict]:
    """Preço médio de um combustível (gasolina, etanol, diesel, diesel-s10,
    gnv, glp) por estado, ou por cidade quando uf é informada."""
    params: dict = {"combustivel": combustivel}
    if uf:
        params.update(por="municipio", uf=uf)
    return (await _get()["anp"].fetch("precos", **params)).dados


if __name__ == "__main__":
    mcp.run()
