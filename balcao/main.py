import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIASGIMiddleware

from balcao import connectors  # noqa: F401  o import registra as fontes
from balcao.arquivos import ArquivoVotos
from balcao.cache import CacheRespostas
from balcao.config import get_settings
from balcao.connectors.base import connector_classes
from balcao.exceptions import BalcaoError
from balcao.http import cria_client
from balcao.logs import configura_logging, loga
from balcao.ratelimit import cria_limiter, le_chaves
from balcao.resilience import CircuitBreaker
from balcao.routers import meta, sources, unified
from balcao.seguranca import ArquivosSeguranca
from balcao.siconv import ArquivosSiconv


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    client = cria_client(settings)
    app.state.client = client
    app.state.cache = CacheRespostas(
        ttl=settings.cache_ttl, stale_ttl=settings.cache_stale_ttl
    )
    # cache separado, de vida curta, pras fontes tempo-real (câmbio)
    app.state.cache_vivo = CacheRespostas(
        ttl=settings.cache_vivo_ttl, stale_ttl=settings.cache_stale_ttl
    )
    app.state.connectors = {
        name: cls(
            client,
            retry_tentativas=settings.retry_tentativas,
            breaker=CircuitBreaker(settings.breaker_falhas, settings.breaker_cooldown),
        )
        for name, cls in connector_classes().items()
    }
    # índice file-backed dos votos anuais da Câmara (histórico completo)
    app.state.arquivo_votos = ArquivoVotos(client)
    # CSVs diários do SICONV: a nota de empenho e o contrato final das obras
    app.state.siconv = ArquivosSiconv(client)
    # ZIP anual do Sinesp (ocorrências criminais) — injetado no conector
    app.state.seguranca = ArquivosSeguranca(client)
    app.state.connectors["seguranca"]._arquivos = app.state.seguranca
    yield
    await client.aclose()


def create_app() -> FastAPI:
    settings = get_settings()
    logger = configura_logging(settings.debug)

    app = FastAPI(
        title="Balcão",
        version="0.1.0",
        description=(
            "Gateway que unifica APIs públicas brasileiras numa porta só, "
            "com schema normalizado, cache e resiliência."
        ),
        lifespan=lifespan,
        # base dos exemplos na doc. Relativo ("/") por padrão pra bater sempre
        # com onde está servido; sem isso o Scalar chuta e duplica o host.
        servers=[{"url": settings.public_url or "/"}],
    )

    # a variante ASGI e a unica que aceita exception handler async
    app.state.limiter = cria_limiter(settings.rate_limit, le_chaves(settings.api_keys))
    app.add_middleware(SlowAPIASGIMiddleware)

    # CORS: a API e so leitura (GET), entao libera so isso pras origens do allowlist.
    # fica por fora do rate-limit pra o preflight (OPTIONS) nao gastar balde.
    origens = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    if origens:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origens,
            allow_methods=["GET", "OPTIONS"],
            allow_headers=["*"],
            max_age=3600,
        )

    # rotas exatas (/v1/fontes, /v1/buscar, /v1/gastos) antes da generica
    # /v1/{fonte}/{recurso}, senao "buscar" viraria nome de fonte
    app.include_router(meta.router)
    app.include_router(unified.router)
    app.include_router(sources.router)

    @app.middleware("http")
    async def loga_requisicoes(request: Request, call_next):
        inicio = time.perf_counter()
        response = await call_next(request)
        # cabeçalhos de segurança pra exposição pública: a API é só JSON,
        # então nada de sniffing, frames ou referrer vazando
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        ms = round((time.perf_counter() - inicio) * 1000, 1)
        dados = {
            "metodo": request.method,
            "caminho": request.url.path,
            "status": response.status_code,
            "ms": ms,
        }
        cache = getattr(request.state, "cache", None)
        if cache:
            dados["cache"] = cache
        loga(logger, "request", **dados)
        return response

    @app.exception_handler(BalcaoError)
    async def trata_erro_balcao(request: Request, exc: BalcaoError) -> JSONResponse:
        corpo = {"erro": exc.mensagem}
        if exc.detalhes:
            corpo["detalhes"] = exc.detalhes
        return JSONResponse(status_code=exc.status_code, content=corpo)

    @app.exception_handler(RateLimitExceeded)
    async def trata_rate_limit(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content={"erro": "muitas requisicoes, tente de novo em instantes"},
        )

    return app


app = create_app()
