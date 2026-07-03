from datetime import datetime

from fastapi import APIRouter, Request

from balcao.cache import CacheRespostas
from balcao.connectors.base import NormalizedResponse
from balcao.exceptions import ErroUpstream, FonteNaoEncontrada

router = APIRouter(prefix="/v1", tags=["fontes"])


@router.get("/{fonte}/{recurso:path}", response_model=NormalizedResponse)
async def consulta_fonte(fonte: str, recurso: str, request: Request) -> NormalizedResponse:
    """Passthrough normalizado: resolve o conector da fonte e repassa o
    recurso com os query params. Ex: /v1/camara/deputados?uf=SP"""
    conectores = request.app.state.connectors
    conector = conectores.get(fonte)
    if conector is None:
        raise FonteNaoEncontrada(fonte, sorted(conectores))
    params = dict(request.query_params)

    cache: CacheRespostas = request.app.state.cache
    # fontes em tempo real (cotações) não passam pelo cache: o valor muda a
    # cada minuto, então cada request busca fresco na fonte
    if not conector.cacheavel:
        request.state.cache = "ao vivo"
        return await conector.fetch(recurso, **params)

    chave = cache.chave(fonte, recurso, params)
    guardada = cache.pega(chave)
    if guardada is not None:
        request.state.cache = "hit"
        return guardada.model_copy(update={"meta": {**guardada.meta, "cache": "hit"}})

    request.state.cache = "miss"
    try:
        resposta = await conector.fetch(recurso, **params)
    except ErroUpstream as exc:
        # fonte caida: dado velho e melhor que erro, quando existir — mas o
        # leitor merece saber de quando ele e (salvo_em)
        guardado = cache.pega_velho(chave)
        if guardado is None:
            raise
        velha, salvo_epoch = guardado
        salvo_em = datetime.fromtimestamp(salvo_epoch).astimezone().isoformat(
            timespec="seconds"
        )
        request.state.cache = "stale"
        return velha.model_copy(
            update={
                "meta": {
                    **velha.meta,
                    "cache": "stale",
                    "aviso": exc.mensagem,
                    "salvo_em": salvo_em,
                }
            }
        )
    cache.guarda(chave, resposta)
    return resposta
