from fastapi import APIRouter, Request

from balcao.cache import CacheRespostas
from balcao.connectors.base import NormalizedResponse
from balcao.exceptions import ErroUpstream, FonteNaoEncontrada
from balcao.projecao import aplica_campos, parse_campos

router = APIRouter(prefix="/v1", tags=["fontes"])


@router.get("/{fonte}/{recurso:path}", response_model=NormalizedResponse)
async def consulta_fonte(fonte: str, recurso: str, request: Request) -> NormalizedResponse:
    """Passthrough normalizado: resolve o conector da fonte e repassa o
    recurso com os query params. Ex: /v1/camara/deputados?uf=SP

    O ?campos=nome,valor recorta cada item pros campos pedidos — é tratado
    aqui, não vai pro conector nem entra na chave de cache (a resposta cheia
    é cacheada e o recorte acontece na borda, compartilhando o cache)."""
    conectores = request.app.state.connectors
    conector = conectores.get(fonte)
    if conector is None:
        raise FonteNaoEncontrada(fonte, sorted(conectores))
    params = dict(request.query_params)
    campos = parse_campos(params.pop("campos", None))

    cache: CacheRespostas = request.app.state.cache
    chave = cache.chave(fonte, recurso, params)
    guardada = cache.pega(chave)
    if guardada is not None:
        request.state.cache = "hit"
        resposta = guardada.model_copy(update={"meta": {**guardada.meta, "cache": "hit"}})
        return aplica_campos(resposta, campos)

    request.state.cache = "miss"
    try:
        resposta = await conector.fetch(recurso, **params)
    except ErroUpstream as exc:
        # fonte caida: dado velho e melhor que erro, quando existir
        velha = cache.pega_velho(chave)
        if velha is None:
            raise
        request.state.cache = "stale"
        resposta = velha.model_copy(
            update={"meta": {**velha.meta, "cache": "stale", "aviso": exc.mensagem}}
        )
        return aplica_campos(resposta, campos)
    cache.guarda(chave, resposta)
    return aplica_campos(resposta, campos)
