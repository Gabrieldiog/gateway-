from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from balcao import connectors  # noqa: F401  o import registra as fontes
from balcao.config import get_settings
from balcao.connectors.base import connector_classes
from balcao.exceptions import BalcaoError
from balcao.http import cria_client
from balcao.routers import meta, sources


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    client = cria_client(settings)
    app.state.client = client
    app.state.connectors = {
        name: cls(client) for name, cls in connector_classes().items()
    }
    yield
    await client.aclose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Balcão",
        version="0.1.0",
        description=(
            "Gateway que unifica APIs públicas brasileiras numa porta só, "
            "com schema normalizado, cache e resiliência."
        ),
        lifespan=lifespan,
    )
    # meta primeiro: /v1/fontes e rota exata e nao pode cair na generica /v1/{fonte}
    app.include_router(meta.router)
    app.include_router(sources.router)

    @app.exception_handler(BalcaoError)
    async def trata_erro_balcao(request: Request, exc: BalcaoError) -> JSONResponse:
        corpo = {"erro": exc.mensagem}
        if exc.detalhes:
            corpo["detalhes"] = exc.detalhes
        return JSONResponse(status_code=exc.status_code, content=corpo)

    return app


app = create_app()
