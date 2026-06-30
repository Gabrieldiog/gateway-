"""Núcleo cross-fonte, sem FastAPI: a busca em leque e a agregação de
gastos. Reusado pelo router HTTP e pelo MCP server — o mesmo miolo
respondendo por duas portas."""

import asyncio
import unicodedata
from collections import defaultdict
from decimal import Decimal

from balcao.connectors.base import BaseConnector
from balcao.connectors.tesouro import CAPITAIS, FONTE as FONTE_TESOURO, UF_IBGE
from balcao.exceptions import (
    BalcaoError,
    FonteNaoEncontrada,
    ParametroInvalido,
    RecursoNaoEncontrado,
)
from balcao.normalize import normaliza_uf

# como o cliente pode chamar a União
UNIAO_APELIDOS = {"brasil", "uniao", "união", "pais", "país", "federal", "governo federal", "br"}


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


def _sem_acento(texto: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).casefold().strip()


async def _municipio_por_nome(ibge: BaseConnector, nome: str, uf: str | None) -> int:
    """Resolve o código IBGE de um município pelo nome. Se o mesmo nome existe
    em vários estados (e é comum), pede a UF pra desambiguar."""
    sigla = normaliza_uf(uf) if uf else None
    lista = await ibge.fetch("municipios", **({"uf": sigla} if sigla else {}))
    alvo = _sem_acento(nome)
    exatos = [m for m in lista.dados if _sem_acento(m["nome"]) == alvo]
    candidatos = exatos or [m for m in lista.dados if alvo in _sem_acento(m["nome"])]
    if not candidatos:
        raise RecursoNaoEncontrado("ibge", f"município {nome!r}", ["municipios?uf="])
    if len(candidatos) > 1 and not sigla:
        ufs = sorted({m["uf"] for m in candidatos if m.get("uf")})
        raise ParametroInvalido(
            f"arrecadacao?ente={nome}", ["uf"], [f"{nome} existe em {', '.join(ufs)} — informe a uf"]
        )
    return candidatos[0]["id"]


async def _resolve_ente(
    ibge: BaseConnector, ente: str, uf: str | None
) -> tuple[str, str]:
    """Descobre o nível do ente e o recurso-base do Tesouro a consultar.
    Aceita 'brasil', uma sigla de UF, um código IBGE ou um nome de cidade."""
    termo = ente.strip()
    if _sem_acento(termo) in UNIAO_APELIDOS:
        return "uniao", "uniao"
    if termo.isdigit():
        return "municipio", f"municipios/{termo}"
    sigla = normaliza_uf(termo)
    if sigla:
        return "estado", f"estados/{sigla}"
    cod = await _municipio_por_nome(ibge, termo, uf)
    return "municipio", f"municipios/{cod}"


async def arrecadacao_ente(
    tesouro: BaseConnector, ibge: BaseConnector, ente: str, ano: int, uf: str | None = None
) -> dict:
    """O pacote de arrecadação de um ente: panorama + quebra por imposto +
    despesa por função, numa chamada só. Resolve 'brasil'/UF/código/nome e
    dispara as três consultas em paralelo."""
    nivel, base = await _resolve_ente(ibge, ente, uf)

    panorama, impostos, despesas = await asyncio.gather(
        tesouro.fetch(base, ano=str(ano)),
        tesouro.fetch(f"{base}/impostos", ano=str(ano)),
        tesouro.fetch(f"{base}/despesas", ano=str(ano)),
        return_exceptions=True,
    )
    if isinstance(panorama, BaseException):
        raise panorama
    if not panorama.dados:
        return {
            "ente": {"nivel": nivel, "ente": ente, "ano": ano},
            "ano": ano,
            "total_impostos": None,
            "impostos": [],
            "despesas": [],
            "fonte": FONTE_TESOURO,
            "meta": {"aviso": panorama.meta.get("aviso", "o Tesouro não tem contas desse ente nesse ano")},
        }
    imp = None if isinstance(impostos, BaseException) else impostos
    desp = None if isinstance(despesas, BaseException) else despesas
    return {
        "ente": panorama.dados[0],
        "ano": ano,
        "total_impostos": imp.meta.get("total_impostos") if imp else None,
        "impostos": imp.dados if imp else [],
        "despesas": desp.dados if desp else [],
        "fonte": FONTE_TESOURO,
        "meta": {},
    }


async def ranking_arrecadacao(
    tesouro: BaseConnector,
    nivel: str,
    ano: int,
    imposto: str | None = None,
    por: str = "total",
    limit: int = 27,
) -> dict:
    """Ranqueia entes por arrecadação. Como o SICONFI só responde um ente por
    vez, isso só fecha em conjuntos pequenos: os 27 estados (cobertura total)
    ou as 27 capitais (uma amostra das maiores cidades). Varre em paralelo,
    com teto de concorrência pra não martelar a fonte."""
    if nivel == "estado":
        alvos = [(uf, f"estados/{uf}") for uf in UF_IBGE]
    elif nivel == "capital":
        alvos = [(uf, f"municipios/{cod}") for uf, cod in CAPITAIS.items()]
    else:
        raise ParametroInvalido("arrecadacao/ranking", [f"nivel={nivel}"], ["estado", "capital"])

    sigla = imposto.upper() if imposto else None
    porta = asyncio.Semaphore(10)

    async def puxa(uf: str, base: str):
        async with porta:
            try:
                return uf, await tesouro.fetch(f"{base}/impostos", ano=str(ano))
            except BalcaoError:
                return uf, None

    respostas = await asyncio.gather(*(puxa(uf, base) for uf, base in alvos))

    linhas: list[dict] = []
    for uf, resp in respostas:
        if resp is None or not resp.dados:
            continue
        pop = resp.meta.get("populacao")
        total = Decimal(str(resp.meta.get("total_impostos") or "0"))
        if sigla:
            bruto = next((Decimal(i["valor"]) for i in resp.dados if i["sigla"] == sigla), Decimal(0))
        else:
            bruto = total
        valor = bruto / pop if (por == "per_capita" and pop) else bruto
        linhas.append(
            {
                "ente": resp.dados[0].get("ente", uf),
                "uf": uf,
                "nivel": nivel,
                "populacao": pop,
                "total_impostos": str(total),
                "valor": str(valor),
            }
        )

    linhas.sort(key=lambda r: Decimal(r["valor"]), reverse=True)
    return {
        "nivel": nivel,
        "ano": ano,
        "imposto": sigla,
        "por": por,
        "total_entes": len(linhas),
        "ranking": linhas[:limit],
    }
