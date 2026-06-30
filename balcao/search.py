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


async def _resolve_deputado(
    camara: BaseConnector, deputado: str, uf: str | None = None
) -> dict:
    """Acha o deputado por id (exato) ou por nome (primeiro resultado)."""
    if deputado.strip().isdigit():
        detalhe = await camara.fetch(f"deputados/{int(deputado)}")
        return detalhe.dados[0]
    filtros: dict = {"nome": deputado.strip()}
    if uf and normaliza_uf(uf):
        filtros["uf"] = uf
    lista = await camara.fetch("deputados", **filtros)
    if not lista.dados:
        raise RecursoNaoEncontrado("camara", f"deputado {deputado!r}", ["deputados?nome="])
    return lista.dados[0]


async def gastos_deputado(
    camara: BaseConnector, deputado: str, ano: int, uf: str | None = None
) -> dict:
    """Resolve o deputado por id ou nome e agrega as despesas por tipo."""
    achado = await _resolve_deputado(camara, deputado, uf)

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


async def votos_deputado(
    camara: BaseConnector, deputado: str, votacoes: int = 30, uf: str | None = None
) -> dict:
    """O histórico de voto de um deputado. A API da Câmara é centrada na
    votação (não existe 'votos de um deputado'), então o Balcão pega as
    votações recentes do plenário, busca o voto de cada uma em paralelo e
    extrai o voto desta pessoa. Votação simbólica não registra voto individual
    e simplesmente não aparece."""
    achado = await _resolve_deputado(camara, deputado, uf)

    recentes = await camara.fetch("votacoes", orgao="180", itens=str(votacoes))
    alvos = recentes.dados

    # cada votos é uma chamada lenta da Câmara; dispara todas em paralelo com
    # teto de tempo por chamada — a que estourar é descartada, não trava o lote.
    async def busca_votos(vid: str):
        return await asyncio.wait_for(camara.fetch(f"votacoes/{vid}/votos"), timeout=6)

    detalhes = await asyncio.gather(
        *(busca_votos(v["id"]) for v in alvos),
        return_exceptions=True,
    )

    historico: list[dict] = []
    for votacao, votos in zip(alvos, detalhes):
        if isinstance(votos, BaseException):
            continue
        meu = next((x for x in votos.dados if x["deputado_id"] == achado["id"]), None)
        if meu is None:
            continue  # simbólica, ou o deputado não estava na votação
        historico.append(
            {
                "votacao_id": votacao["id"],
                "data": votacao["data"],
                "descricao": votacao["descricao"],
                "aprovada": votacao["aprovada"],
                "voto": meu["voto"],
            }
        )

    return {
        "fonte": "camara",
        "casa": "camara",
        "parlamentar": achado,
        "analisadas": len(alvos),
        "total": len(historico),
        "votos": historico,
    }


async def votos_deputado_ano(camara: BaseConnector, deputado: str, ano: int, arquivo) -> dict:
    """O histórico COMPLETO de um deputado num ano, do arquivo anual da Câmara
    (centenas de votos, não só a sessão recente). Resolve a pessoa, pega o
    índice do ano (montado uma vez) e junta cada voto com a descrição da votação."""
    achado = await _resolve_deputado(camara, deputado)
    idx = await arquivo.indice(ano)
    brutos = idx.por_deputado.get(achado["id"], [])

    historico = []
    for vb in brutos:
        info = idx.por_votacao.get(vb["votacao_id"], {})
        historico.append(
            {
                "votacao_id": vb["votacao_id"],
                "data": vb["data"] or info.get("data"),
                "descricao": info.get("descricao") or f"Votação {vb['votacao_id']}",
                "aprovada": info.get("aprovada"),
                "voto": vb["voto"],
            }
        )
    historico.sort(key=lambda v: v["data"] or "", reverse=True)
    return {
        "fonte": "camara",
        "casa": "camara",
        "parlamentar": achado,
        "analisadas": len(brutos),
        "total": len(historico),
        "votos": historico,
    }


async def votos_senador(senado: BaseConnector, senador: str) -> dict:
    """O histórico de voto de um senador. Diferente da Câmara, o Senado
    entrega tudo numa chamada só (a API nova filtra por parlamentar), então
    aqui não há fan-out — e o histórico vem completo, não só o recente."""
    alvo = senador.strip()
    if alvo.isdigit():
        detalhe = await senado.fetch(f"senadores/{int(alvo)}")
        achado = detalhe.dados[0]
    else:
        lista = await senado.fetch("senadores")
        termo = alvo.casefold()
        achado = next((s for s in lista.dados if termo in s["nome"].casefold()), None)
        if achado is None:
            raise RecursoNaoEncontrado("senado", f"senador {senador!r}", ["senadores"])

    votos = await senado.fetch(f"senadores/{achado['id']}/votos")
    return {
        "fonte": "senado",
        "casa": "senado",
        "parlamentar": achado,
        "analisadas": votos.total,
        "total": votos.total,
        "votos": votos.dados,
    }
