"""Núcleo cross-fonte, sem FastAPI: a busca em leque e a agregação de
gastos. Reusado pelo router HTTP e pelo MCP server — o mesmo miolo
respondendo por duas portas."""

import asyncio
from collections import defaultdict
from decimal import Decimal

from balcao.connectors.base import BaseConnector
from balcao.exceptions import BalcaoError, FonteNaoEncontrada, RecursoNaoEncontrado
from balcao.normalize import normaliza_uf


async def busca_unificada(
    conectores: dict[str, BaseConnector], q: str, nomes: list[str] | None = None
) -> dict:
    """Dispara as fontes em paralelo e junta o resultado. Erro numa fonte
    vai pra `erros` sem derrubar as outras."""
    if nomes:
        for nome in nomes:
            if nome not in conectores:
                raise FonteNaoEncontrada(nome, sorted(conectores))
    else:
        nomes = sorted(conectores)
    alvos = [(n, conectores[n]) for n in nomes if conectores[n].suporta_busca]

    saidas = await asyncio.gather(
        *(c.buscar(q) for _, c in alvos), return_exceptions=True
    )
    resultados: list[dict] = []
    erros: dict[str, str] = {}
    for (nome, _), saida in zip(alvos, saidas):
        if isinstance(saida, BaseException):
            erros[nome] = (
                saida.mensagem if isinstance(saida, BalcaoError) else "falha inesperada"
            )
        else:
            resultados.extend(saida)

    return {
        "q": q,
        "fontes_consultadas": [n for n, _ in alvos],
        "total": len(resultados),
        "resultados": resultados,
        "erros": erros,
    }


async def gastos_deputado(
    camara: BaseConnector, deputado: str, ano: int, uf: str | None = None
) -> dict:
    """Resolve o deputado por id ou nome e agrega as despesas por tipo."""
    if deputado.strip().isdigit():
        detalhe = await camara.fetch(f"deputados/{int(deputado)}")
        achado = detalhe.dados[0]
    else:
        filtros: dict = {"nome": deputado.strip()}
        if uf and normaliza_uf(uf):
            filtros["uf"] = uf
        lista = await camara.fetch("deputados", **filtros)
        if not lista.dados:
            raise RecursoNaoEncontrado("camara", f"deputado {deputado!r}", ["deputados?nome="])
        achado = lista.dados[0]

    # a CEAP rende centenas de documentos por ano; sem paginar, o total sai
    # truncado em 100. Pagina até acabar, com teto pra não disparar sem limite.
    documentos: list[dict] = []
    pagina = 1
    while True:
        lote = await camara.fetch(
            f"deputados/{achado['id']}/despesas",
            ano=str(ano),
            itens="100",
            pagina=str(pagina),
        )
        documentos.extend(lote.dados)
        if not lote.meta.get("tem_proxima") or pagina >= 20:
            break
        pagina += 1

    total = Decimal("0")
    por_tipo: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for item in documentos:
        valor = Decimal(item["valor"])
        total += valor
        por_tipo[item["tipo"]] += valor

    return {
        "fonte": "camara",
        "deputado": achado,
        "ano": ano,
        "total_documentos": len(documentos),
        "valor_total": str(total),
        "por_tipo": {tipo: str(valor) for tipo, valor in sorted(por_tipo.items())},
    }
