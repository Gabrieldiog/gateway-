"""As rotas cross-fonte: /v1/buscar dispara as fontes em paralelo e junta
o resultado; /v1/gastos resolve o parlamentar e agrega as despesas. A
lógica vive em balcao/search.py; aqui ficam só HTTP, cache e schema."""

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field

from balcao.search import busca_unificada, gastos_deputado, votos_deputado, votos_senador

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
) -> VotosParlamentarOut:
    # Câmara varre N votações (caro) e o Senado faz uma chamada só; ambos
    # cacheiam o resultado pra não repetir o trabalho.
    cache = request.app.state.cache
    chave = cache.chave("_votos", f"{casa}:{parlamentar.lower()}", {"v": votacoes})
    guardada = cache.pega(chave)
    if guardada is not None:
        request.state.cache = "hit"
        return guardada

    request.state.cache = "miss"
    if casa == "senado":
        senado = request.app.state.connectors["senado"]
        resultado = await votos_senador(senado, parlamentar)
    else:
        camara = request.app.state.connectors["camara"]
        resultado = await votos_deputado(camara, parlamentar, votacoes)
    resposta = VotosParlamentarOut(**resultado)
    cache.guarda(chave, resposta)
    return resposta
