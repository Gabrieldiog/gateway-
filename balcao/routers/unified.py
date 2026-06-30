"""As rotas cross-fonte: /v1/buscar dispara as fontes em paralelo e junta
o resultado; /v1/gastos resolve o parlamentar e agrega as despesas. A
lógica vive em balcao/search.py; aqui ficam só HTTP, cache e schema."""

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field

from balcao.search import (
    arrecadacao_ente,
    busca_unificada,
    gastos_deputado,
    ranking_arrecadacao,
    votos_deputado,
    votos_deputado_ano,
    votos_senador,
)

router = APIRouter(prefix="/v1", tags=["unificado"])


class BuscaOut(BaseModel):
    q: str
    fontes_consultadas: list[str]
    total: int
    resultados: list[dict]
    erros: dict[str, str] = Field(default_factory=dict)
    meta: dict = Field(default_factory=dict)


class GastosOut(BaseModel):
    fonte: str = "camara"
    deputado: dict
    ano: int
    total_documentos: int
    valor_total: str
    por_tipo: dict[str, str]


class VotosParlamentarOut(BaseModel):
    fonte: str
    casa: str  # camara | senado
    parlamentar: dict
    analisadas: int
    total: int
    votos: list[dict]


class ArrecadacaoOut(BaseModel):
    ente: dict  # o panorama: nivel, nome, uf, receita, impostos, despesa
    ano: int
    total_impostos: str | None = None
    impostos: list[dict]  # quanto veio de cada imposto
    despesas: list[dict]  # pra onde foi, por função
    meta: dict = Field(default_factory=dict)


class RankingOut(BaseModel):
    nivel: str  # estado | capital
    ano: int
    imposto: str | None = None  # sigla quando o ranking é por um imposto só
    por: str  # total | per_capita
    total_entes: int
    ranking: list[dict]


@router.get("/buscar", response_model=BuscaOut)
async def buscar(
    request: Request,
    q: str = Query(min_length=2, description="termo de busca"),
    fontes: str | None = Query(None, description="ex: camara,senado; vazio = todas"),
) -> BuscaOut:
    conectores = request.app.state.connectors
    nomes = [n.strip() for n in fontes.split(",") if n.strip()] if fontes else None

    cache = request.app.state.cache
    chave = cache.chave("_buscar", q.lower(), {"fontes": fontes or "todas"})
    guardada = cache.pega(chave)
    if guardada is not None:
        request.state.cache = "hit"
        return guardada

    request.state.cache = "miss"
    resultado = await busca_unificada(conectores, q, nomes)
    resposta = BuscaOut(**resultado)
    if not resultado["erros"]:
        cache.guarda(chave, resposta)
    return resposta


@router.get("/arrecadacao", response_model=ArrecadacaoOut)
async def arrecadacao(
    request: Request,
    ente: str = Query(description="brasil, uma UF (GO), um código IBGE (5208707) ou o nome da cidade"),
    ano: int = Query(2023, ge=2013, description="ano do balanço; 2023 é o mais completo"),
    uf: str | None = Query(None, description="desempata quando o nome da cidade existe em vários estados"),
) -> ArrecadacaoOut:
    # dado anual e estável: cacheia o pacote inteiro com folga
    cache = request.app.state.cache
    chave = cache.chave("_arrecadacao", ente.lower(), {"ano": ano, "uf": (uf or "").upper()})
    guardada = cache.pega(chave)
    if guardada is not None:
        request.state.cache = "hit"
        return guardada

    request.state.cache = "miss"
    conectores = request.app.state.connectors
    resultado = await arrecadacao_ente(conectores["tesouro"], conectores["ibge"], ente, ano, uf)
    resposta = ArrecadacaoOut(**resultado)
    cache.guarda(chave, resposta)
    return resposta


@router.get("/arrecadacao/ranking", response_model=RankingOut)
async def arrecadacao_ranking(
    request: Request,
    nivel: str = Query("estado", pattern="^(estado|capital)$", description="estado (27) ou capital (27)"),
    ano: int = Query(2023, ge=2013),
    imposto: str | None = Query(None, description="sigla pra ranquear por um imposto só (ICMS, ISS, IPTU...)"),
    por: str = Query("total", pattern="^(total|per_capita)$", description="total arrecadado ou por habitante"),
    limit: int = Query(27, ge=1, le=27),
) -> RankingOut:
    # varre 27 entes; dado anual e estável, então cacheia o ranking inteiro
    cache = request.app.state.cache
    chave = cache.chave(
        "_ranking", nivel, {"ano": ano, "imposto": (imposto or "").upper(), "por": por, "limit": limit}
    )
    guardada = cache.pega(chave)
    if guardada is not None:
        request.state.cache = "hit"
        return guardada

    request.state.cache = "miss"
    tesouro = request.app.state.connectors["tesouro"]
    resultado = await ranking_arrecadacao(tesouro, nivel, ano, imposto, por, limit)
    resposta = RankingOut(**resultado)
    cache.guarda(chave, resposta)
    return resposta


@router.get("/gastos", response_model=GastosOut)
async def gastos(
    request: Request,
    deputado: str = Query(description="id ou nome do deputado"),
    ano: int = Query(2026, ge=2008),
    uf: str | None = None,
) -> GastosOut:
    camara = request.app.state.connectors["camara"]
    resultado = await gastos_deputado(camara, deputado, ano, uf)
    return GastosOut(**resultado)


@router.get("/votos", response_model=VotosParlamentarOut)
async def votos(
    request: Request,
    parlamentar: str = Query(description="id ou nome do parlamentar"),
    casa: str = Query("camara", pattern="^(camara|senado)$", description="camara ou senado"),
    votacoes: int = Query(25, ge=5, le=80, description="Câmara: quantas votações recentes varrer"),
    ano: int | None = Query(None, ge=2008, description="Câmara: histórico completo de um ano (arquivo)"),
) -> VotosParlamentarOut:
    # Câmara varre N votações (caro) ou lê o ano inteiro do arquivo; o Senado
    # faz uma chamada só. Tudo cacheia o resultado pra não repetir o trabalho.
    cache = request.app.state.cache
    chave = cache.chave("_votos", f"{casa}:{parlamentar.lower()}", {"v": votacoes, "ano": ano or 0})
    guardada = cache.pega(chave)
    if guardada is not None:
        request.state.cache = "hit"
        return guardada

    request.state.cache = "miss"
    if casa == "senado":
        senado = request.app.state.connectors["senado"]
        resultado = await votos_senador(senado, parlamentar)
    elif ano is not None:
        camara = request.app.state.connectors["camara"]
        resultado = await votos_deputado_ano(camara, parlamentar, ano, request.app.state.arquivo_votos)
    else:
        camara = request.app.state.connectors["camara"]
        resultado = await votos_deputado(camara, parlamentar, votacoes)
    resposta = VotosParlamentarOut(**resultado)
    cache.guarda(chave, resposta)
    return resposta
