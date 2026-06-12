from contextlib import asynccontextmanager

from fastapi import FastAPI

from balcao import connectors  # noqa: F401  o import registra as fontes
from balcao.config import get_settings
from balcao.connectors.base import connector_classes
from balcao.http import cria_client
from balcao.routers import meta


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
    app.include_router(meta.router)
    return app


app = create_app()
