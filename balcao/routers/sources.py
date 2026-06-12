from fastapi import APIRouter, Request

from balcao.connectors.base import NormalizedResponse
from balcao.exceptions import FonteNaoEncontrada

router = APIRouter(prefix="/v1", tags=["fontes"])


@router.get("/{fonte}/{recurso:path}", response_model=NormalizedResponse)
async def consulta_fonte(fonte: str, recurso: str, request: Request) -> NormalizedResponse:
    """Passthrough normalizado: resolve o conector da fonte e repassa o
    recurso com os query params. Ex: /v1/camara/deputados?uf=SP"""
    conectores = request.app.state.connectors
    conector = conectores.get(fonte)
    if conector is None:
        raise FonteNaoEncontrada(fonte, sorted(conectores))
    return await conector.fetch(recurso, **dict(request.query_params))
