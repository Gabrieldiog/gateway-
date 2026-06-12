"""As rotas cross-fonte: /v1/buscar dispara as fontes em paralelo e junta
o resultado; /v1/gastos resolve o parlamentar e agrega as despesas."""

import asyncio
from collections import defaultdict
from decimal import Decimal

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field

from balcao.exceptions import BalcaoError, FonteNaoEncontrada, RecursoNaoEncontrado
from balcao.normalize import normaliza_uf

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


@router.get("/buscar", response_model=BuscaOut)
async def buscar(
    request: Request,
    q: str = Query(min_length=2, description="termo de busca"),
    fontes: str | None = Query(None, description="ex: camara,senado; vazio = todas"),
) -> BuscaOut:
    conectores = request.app.state.connectors

    if fontes:
        nomes = [n.strip() for n in fontes.split(",") if n.strip()]
        for nome in nomes:
            if nome not in conectores:
                raise FonteNaoEncontrada(nome, sorted(conectores))
    else:
        nomes = sorted(conectores)
    alvos = [(n, conectores[n]) for n in nomes if conectores[n].suporta_busca]

    cache = request.app.state.cache
    chave = cache.chave("_buscar", q.lower(), {"fontes": ",".join(n for n, _ in alvos)})
    guardada = cache.pega(chave)
    if guardada is not None:
        request.state.cache = "hit"
        return guardada

    request.state.cache = "miss"
    saidas = await asyncio.gather(
        *(conector.buscar(q) for _, conector in alvos), return_exceptions=True
    )

    resultados: list[dict] = []
    erros: dict[str, str] = {}
    for (nome, _), saida in zip(alvos, saidas):
        if isinstance(saida, BaseException):
            # uma fonte caida nao derruba a busca nas outras
            erros[nome] = saida.mensagem if isinstance(saida, BalcaoError) else "falha inesperada"
        else:
            resultados.extend(saida)

    resposta = BuscaOut(
        q=q,
        fontes_consultadas=[n for n, _ in alvos],
        total=len(resultados),
        resultados=resultados,
        erros=erros,
    )
    if not erros:
        cache.guarda(chave, resposta)
    return resposta


@router.get("/gastos", response_model=GastosOut)
async def gastos(
    request: Request,
    deputado: str = Query(description="id ou nome do deputado"),
    ano: int = Query(2026, ge=2008),
    uf: str | None = None,
) -> GastosOut:
    """Decide a fonte e resolve o parlamentar: aceita id ou nome, busca as
    despesas e devolve o total agregado por tipo."""
    camara = request.app.state.connectors["camara"]

    if deputado.strip().isdigit():
        detalhe = await camara.fetch(f"deputados/{int(deputado)}")
        achado = detalhe.dados[0]
    else:
        filtros = {"nome": deputado.strip()}
        if uf and normaliza_uf(uf):
            filtros["uf"] = uf
        lista = await camara.fetch("deputados", **filtros)
        if not lista.dados:
            raise RecursoNaoEncontrado(
                "camara", f"deputado {deputado!r}", ["deputados?nome="]
            )
        achado = lista.dados[0]

    despesas = await camara.fetch(
        f"deputados/{achado['id']}/despesas", ano=str(ano), itens="100"
    )

    total = Decimal("0")
    por_tipo: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for item in despesas.dados:
        valor = Decimal(item["valor"])
        total += valor
        por_tipo[item["tipo"]] += valor

    return GastosOut(
        deputado=achado,
        ano=ano,
        total_documentos=len(despesas.dados),
        valor_total=str(total),
        por_tipo={tipo: str(valor) for tipo, valor in sorted(por_tipo.items())},
    )
