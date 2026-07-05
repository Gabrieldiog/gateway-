from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

router = APIRouter(tags=["meta"])

# referência da API estilo Scalar, montada do próprio OpenAPI que o FastAPI já
# gera — try-it no navegador e exemplos de código em várias linguagens. O
# FastAPI ainda serve /docs (Swagger) e /redoc; esta é a versão bonita.
SCALAR_HTML = """<!doctype html>
<html>
<head>
  <title>Balcão — Referência da API</title>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <link rel="icon" href="data:," />
</head>
<body>
  <script id="api-reference" data-url="/openapi.json"></script>
  <script src="https://cdn.jsdelivr.net/npm/@scalar/api-reference"></script>
</body>
</html>"""


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


# aceita HEAD além de GET: monitores de uptime (UptimeRobot etc.) batem HEAD
# por padrão, e um health check que só aceita GET responde 405 pra eles
@router.api_route("/health", methods=["GET", "HEAD"], response_model=HealthOut)
async def health(request: Request) -> HealthOut:
    return HealthOut(status="ok", versao=request.app.version)


@router.get("/scalar", include_in_schema=False)
async def scalar() -> HTMLResponse:
    return HTMLResponse(SCALAR_HTML)


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
