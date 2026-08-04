"""As rotas cross-fonte: /v1/buscar dispara as fontes em paralelo e junta
o resultado; /v1/gastos resolve o parlamentar e agrega as despesas;
/v1/fornecedor cruza um CNPJ em quatro fontes. A lógica de busca vive em
balcao/search.py; aqui ficam HTTP, cache e schema."""

import asyncio
from datetime import date

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field

from balcao.exceptions import BalcaoError, ParametroInvalido
from balcao.normalize import so_digitos

from balcao.search import (
    arrecadacao_ente,
    arrecadacao_todas_esferas,
    busca_unificada,
    dinheiro_da_obra,
    gastos_deputado,
    ranking_arrecadacao,
    votos_deputado,
    votos_deputado_ano,
    votos_senador,
)

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


class FornecedorOut(BaseModel):
    """A ficha follow-the-money de um CNPJ: quem é (Receita), que relação tem
    com o governo federal, sanções e contratos; quatro consultas numa só."""

    cnpj: str
    cadastro: dict | None = None  # ficha da Receita (BrasilAPI)
    vinculos: dict | None = None  # flags do dossiê da Transparência
    sancoes: list[dict] = Field(default_factory=list)
    contratos: list[dict] = Field(default_factory=list)
    erros: dict[str, str] = Field(default_factory=dict)  # falha parcial não derruba
    meta: dict = Field(default_factory=dict)


class VotosParlamentarOut(BaseModel):
    fonte: str
    casa: str  # camara | senado
    parlamentar: dict
    analisadas: int
    total: int
    votos: list[dict]


class ArrecadacaoOut(BaseModel):
    ente: dict  # o panorama: nivel, nome, uf, receita, impostos, despesa
    ano: int
    total_impostos: str | None = None
    impostos: list[dict]  # quanto veio de cada imposto
    despesas: list[dict]  # pra onde foi, por função
    fonte: dict = Field(default_factory=dict)  # de onde o dado vem (verificável)
    meta: dict = Field(default_factory=dict)


class RankingOut(BaseModel):
    nivel: str  # estado | capital
    ano: int
    imposto: str | None = None  # sigla quando o ranking é por um imposto só
    por: str  # total | per_capita
    total_entes: int
    ranking: list[dict]


@router.get("/buscar", response_model=BuscaOut)
async def buscar(
    request: Request,
    q: str = Query(min_length=2, description="termo de busca"),
    fontes: str | None = Query(None, description="ex: camara,senado; vazio = todas"),
) -> BuscaOut:
    conectores = request.app.state.connectors
    nomes = [n.strip() for n in fontes.split(",") if n.strip()] if fontes else None

    cache = request.app.state.cache
    chave = cache.chave("_buscar", q.lower(), {"fontes": fontes or "todas"})
    guardada = cache.pega(chave)
    if guardada is not None:
        request.state.cache = "hit"
        return guardada

    request.state.cache = "miss"
    resultado = await busca_unificada(conectores, q, nomes)
    resposta = BuscaOut(**resultado)
    if not resultado["erros"]:
        cache.guarda(chave, resposta)
    return resposta


@router.get("/arrecadacao", response_model=ArrecadacaoOut)
async def arrecadacao(
    request: Request,
    ente: str = Query(description="brasil, uma UF (GO), um código IBGE (5208707) ou o nome da cidade"),
    ano: int | None = Query(None, ge=2013, description="vazio = o exercício anterior ao corrente"),
    uf: str | None = Query(None, description="desempata quando o nome da cidade existe em vários estados"),
) -> ArrecadacaoOut:
    ano = ano or date.today().year - 1
    # dado anual e estável: cacheia o pacote inteiro com folga
    cache = request.app.state.cache
    chave = cache.chave("_arrecadacao", ente.lower(), {"ano": ano, "uf": (uf or "").upper()})
    guardada = cache.pega(chave)
    if guardada is not None:
        request.state.cache = "hit"
        return guardada

    request.state.cache = "miss"
    conectores = request.app.state.connectors
    resultado = await arrecadacao_ente(conectores["tesouro"], conectores["ibge"], ente, ano, uf)
    resposta = ArrecadacaoOut(**resultado)
    cache.guarda(chave, resposta)
    return resposta


@router.get("/arrecadacao/ranking", response_model=RankingOut)
async def arrecadacao_ranking(
    request: Request,
    nivel: str = Query("estado", pattern="^(estado|capital)$", description="estado (27) ou capital (27)"),
    ano: int | None = Query(None, ge=2013, description="vazio = o exercício anterior ao corrente"),
    imposto: str | None = Query(None, description="sigla pra ranquear por um imposto só (ICMS, ISS, IPTU...)"),
    por: str = Query("total", pattern="^(total|per_capita)$", description="total arrecadado ou por habitante"),
    limit: int = Query(27, ge=1, le=27),
) -> RankingOut:
    ano = ano or date.today().year - 1
    # varre 27 entes; dado anual e estável, então cacheia o ranking inteiro
    cache = request.app.state.cache
    chave = cache.chave(
        "_ranking", nivel, {"ano": ano, "imposto": (imposto or "").upper(), "por": por, "limit": limit}
    )
    guardada = cache.pega(chave)
    if guardada is not None:
        request.state.cache = "hit"
        return guardada

    request.state.cache = "miss"
    tesouro = request.app.state.connectors["tesouro"]
    resultado = await ranking_arrecadacao(tesouro, nivel, ano, imposto, por, limit)
    resposta = RankingOut(**resultado)
    cache.guarda(chave, resposta)
    return resposta


@router.get("/fornecedor/{cnpj:path}", response_model=FornecedorOut)
async def fornecedor(request: Request, cnpj: str) -> FornecedorOut:
    doc = so_digitos(cnpj) or ""
    if len(doc) != 14:
        raise ParametroInvalido("fornecedor", ["cnpj"], ["cnpj de 14 dígitos (com ou sem máscara)"])

    cache = request.app.state.cache
    chave = cache.chave("_fornecedor", doc, {})
    guardada = cache.pega(chave)
    if guardada is not None:
        request.state.cache = "hit"
        return guardada

    request.state.cache = "miss"
    conectores = request.app.state.connectors

    async def pega(fonte: str, recurso: str, **params):
        try:
            return await conectores[fonte].fetch(recurso, **params), None
        except BalcaoError as exc:
            return None, exc.mensagem

    (cad, e_cad), (vin, e_vin), (san, e_san), (con, e_con) = await asyncio.gather(
        pega("brasilapi", f"cnpj/{doc}"),
        pega("transparencia", "vinculos", cnpj=doc),
        pega("transparencia", "sancoes", documento=doc),
        pega("transparencia", "contratos", documento=doc),
    )
    erros = {
        nome: msg
        for nome, msg in (
            ("cadastro", e_cad), ("vinculos", e_vin), ("sancoes", e_san), ("contratos", e_con),
        )
        if msg
    }
    resposta = FornecedorOut(
        cnpj=doc,
        cadastro=cad.dados[0] if cad and cad.dados else None,
        vinculos=vin.dados[0] if vin and vin.dados else None,
        sancoes=san.dados if san else [],
        contratos=con.dados if con else [],
        erros=erros,
        meta={
            "fontes_consultadas": ["brasilapi", "transparencia"],
            "contratos_tem_proxima": bool(con and con.meta.get("tem_proxima")),
        },
    )
    if not erros:
        cache.guarda(chave, resposta)
    return resposta


class ObraDinheiroOut(BaseModel):
    """O follow-the-money de uma obra: empenhos com o favorecido resolvido em
    cascata (Obrasgov → regra orçamentária → CSV SICONV → SIAFI) e o contrato
    final, quem de fato construiu, com CNPJ."""

    id: str
    obra: dict | None = None
    empenhos: list[dict] = Field(default_factory=list)
    total_empenhado: str = "0"
    tem_mais_empenhos: bool = False
    contratos: list[dict] = Field(default_factory=list)  # a empreiteira (SICONV)
    erros: dict[str, str] = Field(default_factory=dict)
    meta: dict = Field(default_factory=dict)


@router.get("/obra/dinheiro", response_model=ObraDinheiroOut)
async def obra_dinheiro(
    request: Request,
    id: str = Query(..., description="idUnico da obra no Obrasgov (ex: 11370.52-41)"),
) -> ObraDinheiroOut:
    id_obra = id.strip()
    if not id_obra:
        raise ParametroInvalido("obra/dinheiro", ["id"], ["idUnico da obra (ex: 11370.52-41)"])

    cache = request.app.state.cache
    chave = cache.chave("_obra_dinheiro", id_obra, {})
    guardada = cache.pega(chave)
    if guardada is not None:
        request.state.cache = "hit"
        return guardada

    request.state.cache = "miss"
    resultado = await dinheiro_da_obra(
        request.app.state.connectors, request.app.state.siconv, id_obra
    )
    resposta = ObraDinheiroOut(**resultado)
    if not resposta.erros:
        cache.guarda(chave, resposta)
    return resposta


class TodasEsferasOut(BaseModel):
    """O bolo tributario somado de verdade: Uniao + 27 estados + 27 capitais,
    balanco a balanco do SICONFI (municipios do interior declaradamente fora)."""

    ano: int
    uniao: str
    estados: str
    capitais: str
    total: str
    entes_somados: int
    meta: dict = Field(default_factory=dict)


@router.get("/arrecadacao/geral", response_model=TodasEsferasOut)
async def arrecadacao_geral(
    request: Request,
    ano: int | None = Query(None, ge=2013, description="vazio = o exercício anterior ao corrente"),
) -> TodasEsferasOut:
    ano = ano or date.today().year - 1
    # 55 consultas ao SICONFI: cacheia o pacote com carinho
    cache = request.app.state.cache
    chave = cache.chave("_todas_esferas", str(ano), {})
    guardada = cache.pega(chave)
    if guardada is not None:
        request.state.cache = "hit"
        return guardada

    request.state.cache = "miss"
    tesouro = request.app.state.connectors["tesouro"]
    resultado = await arrecadacao_todas_esferas(tesouro, ano)
    resposta = TodasEsferasOut(**resultado)
    if resultado["entes_somados"]:
        cache.guarda(chave, resposta)
    return resposta


@router.get("/gastos", response_model=GastosOut)
async def gastos(
    request: Request,
    deputado: str = Query(description="id ou nome do deputado"),
    ano: int | None = Query(None, ge=2008, description="vazio = ano corrente"),
    uf: str | None = None,
) -> GastosOut:
    ano = ano or date.today().year
    camara = request.app.state.connectors["camara"]
    resultado = await gastos_deputado(camara, deputado, ano, uf)
    return GastosOut(**resultado)


@router.get("/votos", response_model=VotosParlamentarOut)
async def votos(
    request: Request,
    parlamentar: str = Query(description="id ou nome do parlamentar"),
    casa: str = Query("camara", pattern="^(camara|senado)$", description="camara ou senado"),
    votacoes: int = Query(25, ge=5, le=80, description="Câmara: quantas votações recentes varrer"),
    ano: int | None = Query(None, ge=2008, description="Câmara: histórico completo de um ano (arquivo)"),
) -> VotosParlamentarOut:
    # Câmara varre N votações (caro) ou lê o ano inteiro do arquivo; o Senado
    # faz uma chamada só. Tudo cacheia o resultado pra não repetir o trabalho.
    cache = request.app.state.cache
    chave = cache.chave("_votos", f"{casa}:{parlamentar.lower()}", {"v": votacoes, "ano": ano or 0})
    guardada = cache.pega(chave)
    if guardada is not None:
        request.state.cache = "hit"
        return guardada

    request.state.cache = "miss"
    if casa == "senado":
        senado = request.app.state.connectors["senado"]
        resultado = await votos_senador(senado, parlamentar)
    elif ano is not None:
        camara = request.app.state.connectors["camara"]
        resultado = await votos_deputado_ano(camara, parlamentar, ano, request.app.state.arquivo_votos)
    else:
        camara = request.app.state.connectors["camara"]
        resultado = await votos_deputado(camara, parlamentar, votacoes)
    resposta = VotosParlamentarOut(**resultado)
    cache.guarda(chave, resposta)
    return resposta
