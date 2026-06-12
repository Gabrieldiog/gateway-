from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(tags=["meta"])


class HealthOut(BaseModel):
    status: str
    versao: str


class FonteOut(BaseModel):
    nome: str
    base_url: str
    precisa_chave: bool
    descricao: str
    recursos: dict[str, str]


class FontesOut(BaseModel):
    total: int
    fontes: list[FonteOut]


@router.get("/health", response_model=HealthOut)
async def health(request: Request) -> HealthOut:
    return HealthOut(status="ok", versao=request.app.version)


@router.get("/v1/fontes", response_model=FontesOut)
async def fontes(request: Request) -> FontesOut:
    conectores = request.app.state.connectors.values()
    itens = [
        FonteOut(
            nome=c.name,
            base_url=c.base_url,
            precisa_chave=c.requires_key,
            descricao=c.description,
            recursos=c.resources,
        )
        for c in conectores
    ]
    return FontesOut(total=len(itens), fontes=itens)
