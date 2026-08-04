import asyncio
import csv
import io
from decimal import Decimal, InvalidOperation
from typing import Any

from pydantic import ValidationError

from balcao.connectors.base import BaseConnector, NormalizedResponse, register
from balcao.exceptions import ErroUpstream, ParametroInvalido, RecursoNaoEncontrado
from balcao.models import IndicadorEconomico, PontoSerie, RankingReclamacao, TaxaJurosBanco
from balcao.normalize import data_br, limpa_texto, para_data, valor_br

# atalhos pros codigos de serie mais pedidos do SGS
SERIES = {
    "selic": 432,
    "cdi": 12,
    "ipca": 433,
    "ipca12m": 13522,  # IPCA acumulado em 12 meses
    "inpc": 188,
    "igpm": 189,
    "igpdi": 190,
    "poupanca": 196,  # rendimento mensal; a 195 é o índice diário de aniversário
    "dolar": 1,
    "euro": 21619,
}

# rótulo e unidade de cada série, usados só no painel de custo de vida
INDICADORES = {
    "ipca": ("IPCA (mês)", "% no mês"),
    "ipca12m": ("IPCA (12 meses)", "% ao ano"),
    "inpc": ("INPC (mês)", "% no mês"),
    "igpm": ("IGP-M (mês)", "% no mês"),
    "igpdi": ("IGP-DI (mês)", "% no mês"),
    "selic": ("Selic (meta)", "% ao ano"),
    "cdi": ("CDI", "% ao dia"),
    "poupanca": ("Poupança", "% no mês"),
    "dolar": ("Dólar (PTAX)", "R$"),
    "euro": ("Euro (PTAX)", "R$"),
}

# o painel "custo de vida": os indicadores que pesam no bolso, na ordem de exibição
PAINEL = ("ipca12m", "ipca", "igpm", "inpc", "selic", "cdi", "poupanca", "dolar")

FONTE = {
    "nome": "Banco Central, Sistema Gerenciador de Séries (SGS)",
    "url": "https://www3.bcb.gov.br/sgspub/",
    "nota": (
        "IPCA, INPC e IGP-M são os índices oficiais de inflação; Selic, CDI e "
        "poupança medem o preço do dinheiro. Valor mais recente publicado pelo BC."
    ),
}

PARAMS_SERIE = {"data_inicio", "data_fim", "ultimos"}

# o ranking de reclamações vive no rdrweb, outro host do BCB
RECLAMACOES_URL = "https://www3.bcb.gov.br/rdrweb/rest/ext/ranking"
TIPOS_RECLAMACOES = {"bancos": "Bancos e financeiras", "consorcios": "Consorcios"}
ROTULO_PERIODO = {"TRIMESTRAL": "trimestre", "SEMESTRAL": "semestre", "MENSAL": "mês", "BIMESTRAL": "bimestre"}

FONTE_RECLAMACOES = {
    "nome": "Banco Central, Ranking de Reclamações",
    "url": "https://www.bcb.gov.br/estabilidadefinanceira/rankingreclamacoes",
    "nota": (
        "Reclamações de clientes registradas no BC e julgadas procedentes, por "
        "milhão de clientes de cada instituição. O BC destaca os grandes (Top 15); "
        "instituição pequena aparece sem índice quando os números não sustentam a conta."
    ),
}


@register
class BacenConnector(BaseConnector):
    name = "bacen"
    base_url = "https://api.bcb.gov.br/dados/serie"
    description = "Banco Central (SGS): Selic, CDI, IPCA, IGP-M, câmbio e mais de 190 séries econômicas"
    suporta_busca = True
    resources = {
        "inflacao": "painel de custo de vida: IPCA, IGP-M, INPC, Selic, CDI, poupança e dólar (valor mais recente)",
        "juros-bancos": "ranking oficial: quanto cada banco cobra numa modalidade de crédito (params: modalidade, limit)",
        "reclamacoes": (
            "ranking oficial de reclamações contra bancos e consórcios "
            "(params: ano, periodo, tipo = bancos|consorcios, grupo = top15|todos, busca, limit; "
            "sem ano vem o mais recente)"
        ),
        "serie/{codigo}": f"pontos de uma série do SGS; filtros: {', '.join(sorted(PARAMS_SERIE))}",
        **{
            apelido: f"atalho pra série {codigo} do SGS"
            for apelido, codigo in SERIES.items()
        },
    }

    async def fetch(self, recurso: str, **params: Any) -> NormalizedResponse:
        partes = [p for p in recurso.strip("/").split("/") if p]
        match partes:
            case ["inflacao"] | ["painel"]:
                return await self._painel(recurso)
            case ["juros-bancos"] | ["juros"]:
                return await self._juros_bancos(recurso, params)
            case ["reclamacoes"]:
                return await self._reclamacoes(recurso, params)
            case [apelido] if apelido in SERIES:
                return await self._serie(recurso, SERIES[apelido], params, nome=apelido)
            case ["serie", codigo] if codigo.isdigit():
                return await self._serie(recurso, int(codigo), params)
            case _:
                raise RecursoNaoEncontrado(self.name, recurso, sorted(self.resources))

    async def _juros_bancos(self, recurso: str, params: dict) -> NormalizedResponse:
        """Ranking oficial: quanto cada banco cobra numa modalidade de crédito,
        na última janela publicada (5 dias úteis). Vive no Olinda (outro host
        do BCB); o $ vai literal na URL porque o Olinda rejeita %24. A fonte
        é lenta, o cache do gateway segura o resto."""
        aceitos = {"modalidade", "limit"}
        invalidos = sorted(set(params) - aceitos)
        if invalidos:
            raise ParametroInvalido(recurso, invalidos, sorted(aceitos))
        limit = str(params.get("limit", 30))
        if not limit.isdigit() or not (1 <= int(limit) <= 100):
            raise ParametroInvalido(recurso, ["limit"], ["limit entre 1 e 100"])
        filtro = ""
        modalidade = str(params.get("modalidade", "")).strip()
        if modalidade:
            texto = modalidade.replace("'", "")
            filtro = f"&$filter=contains(Modalidade,'{texto}')"
        # ordena da janela mais nova pra mais velha e corta na primeira completa
        url = (
            "https://olinda.bcb.gov.br/olinda/servico/taxaJuros/versao/v2/odata/"
            f"TaxasJurosDiariaPorInicioPeriodo?$top=600&$format=json"
            f"&$orderby=InicioPeriodo desc,Posicao{filtro}"
        )
        bruto = await self.get_json(url, timeout=50)
        linhas = bruto.get("value", []) if isinstance(bruto, dict) else []
        itens: list[dict] = []
        janela = None
        for r in linhas:
            inicio = r.get("InicioPeriodo")
            if janela is None:
                janela = (inicio, r.get("FimPeriodo"))
            if inicio != janela[0]:
                break
            try:
                itens.append(
                    TaxaJurosBanco(
                        posicao=int(r.get("Posicao") or 0),
                        instituicao=limpa_texto(r.get("InstituicaoFinanceira")) or "sem dado",
                        modalidade=limpa_texto(r.get("Modalidade")) or "sem dado",
                        mes=inicio,
                        taxa_mes=float(r["TaxaJurosAoMes"]) if r.get("TaxaJurosAoMes") is not None else None,
                        taxa_ano=float(r["TaxaJurosAoAno"]) if r.get("TaxaJurosAoAno") is not None else None,
                    ).model_dump(mode="json")
                )
            except (ValueError, TypeError):
                continue
            if len(itens) >= int(limit):
                break
        meta = {
            "modalidade": modalidade or "todas",
            "janela_de": janela[0] if janela else None,
            "janela_ate": janela[1] if janela else None,
            "fonte": {
                "nome": "Banco Central, ranking de taxas de juros (Olinda)",
                "url": "https://www.bcb.gov.br/estatisticas/txjuros",
                "nota": (
                    "Taxas médias efetivamente cobradas por cada instituição na "
                    "última janela de cinco dias úteis, apuradas e publicadas "
                    "pelo Banco Central."
                ),
            },
        }
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=itens, total=len(itens), meta=meta
        )

    async def buscar(self, q: str) -> list[dict]:
        termo = q.casefold()
        achados = []
        for apelido, codigo in SERIES.items():
            if termo in apelido:
                resposta = await self._serie(apelido, codigo, {"ultimos": "5"}, nome=apelido)
                achados += [
                    {"tipo_resultado": "serie_economica", **p} for p in resposta.dados
                ]
        return achados

    async def _painel(self, recurso: str) -> NormalizedResponse:
        """Junta o valor mais recente dos indicadores que pesam no bolso numa
        resposta só. Dispara as séries em paralelo; se uma fonte falhar, o
        painel volta sem ela em vez de morrer."""

        async def ultimo(chave: str) -> dict | None:
            codigo = SERIES[chave]
            nome, unidade = INDICADORES[chave]
            try:
                resp = await self._serie(chave, codigo, {"ultimos": "1"}, nome=nome)
            except ErroUpstream:
                return None
            if not resp.dados:
                return None
            ponto = resp.dados[-1]
            return IndicadorEconomico(
                chave=chave,
                serie=codigo,
                nome=nome,
                unidade=unidade,
                data=ponto["data"],
                valor=Decimal(str(ponto["valor"])),
            ).model_dump(mode="json")

        resultados = await asyncio.gather(*(ultimo(chave) for chave in PAINEL))
        itens = [r for r in resultados if r is not None]
        meta: dict = {"painel": "custo de vida", "fonte": FONTE}
        faltando = [c for c, r in zip(PAINEL, resultados) if r is None]
        if faltando:
            meta["indisponiveis"] = faltando
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=itens, total=len(itens), meta=meta
        )

    async def _serie(
        self, recurso: str, codigo: int, params: dict, nome: str | None = None
    ) -> NormalizedResponse:
        invalidos = sorted(set(params) - PARAMS_SERIE)
        if invalidos:
            raise ParametroInvalido(recurso, invalidos, sorted(PARAMS_SERIE))

        ultimos = str(params.get("ultimos", ""))
        if ultimos and not ultimos.isdigit():
            raise ParametroInvalido(recurso, ["ultimos"], sorted(PARAMS_SERIE))

        if ultimos:
            path = f"/bcdata.sgs.{codigo}/dados/ultimos/{int(ultimos)}"
            query = {"formato": "json"}
        elif "data_inicio" in params or "data_fim" in params:
            # o SGS quer datas em dd/mm/aaaa; o Balcao aceita ISO e traduz
            query = {"formato": "json"}
            for chave, alvo in (("data_inicio", "dataInicial"), ("data_fim", "dataFinal")):
                if chave in params:
                    valor = data_br(params[chave])
                    if valor is None:
                        raise ParametroInvalido(recurso, [chave], sorted(PARAMS_SERIE))
                    query[alvo] = valor
            path = f"/bcdata.sgs.{codigo}/dados"
        else:
            # sem recorte a serie inteira viria com decadas de pontos
            path = f"/bcdata.sgs.{codigo}/dados/ultimos/20"
            query = {"formato": "json"}

        bruto = await self.get_json(path, params=query)

        # o SGS às vezes devolve {"erro": {...}} com HTTP 200 (ex.: ultimos/1 em
        # série de índice diário); trata como vazio em vez de estourar no laço
        if not isinstance(bruto, list):
            bruto = []

        itens = []
        descartados = 0
        for b in bruto:
            try:
                ponto = PontoSerie(
                    serie=codigo,
                    nome=nome,
                    data=para_data(b.get("data")),
                    valor=Decimal(str(b.get("valor"))),
                )
                itens.append(ponto.model_dump(mode="json"))
            except (ValidationError, KeyError, InvalidOperation):
                descartados += 1

        meta: dict = {"serie": codigo}
        if descartados:
            meta["descartados"] = descartados
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=itens, total=len(itens), meta=meta
        )

    async def _reclamacoes(self, recurso: str, params: dict) -> NormalizedResponse:
        """O ranking que responde "meu banco é ruim?": reclamações procedentes
        por milhão de clientes. Quirks: o CSV chega latin-1 com o header HTTP
        mentindo charset=UTF-8; o índice usa vírgula e vem vazio pra
        instituição pequena; e o nome da coluna de clientes carrega um
        caractere de controle, as colunas são achadas por prefixo."""
        aceitos = {"ano", "periodo", "tipo", "busca", "limit", "grupo"}
        invalidos = sorted(set(params) - aceitos)
        if invalidos:
            raise ParametroInvalido(recurso, invalidos, sorted(aceitos))
        tipo = str(params.get("tipo", "bancos")).lower()
        if tipo not in TIPOS_RECLAMACOES:
            raise ParametroInvalido(recurso, ["tipo"], sorted(TIPOS_RECLAMACOES))
        limit = str(params.get("limit", 20))
        if not limit.isdigit() or not (1 <= int(limit) <= 500):
            raise ParametroInvalido(recurso, ["limit"], ["limit entre 1 e 500"])
        busca = str(params.get("busca", "")).strip().casefold()

        ano = str(params.get("ano", "")).strip()
        periodo = str(params.get("periodo", "")).strip()
        if ano and not ano.isdigit():
            raise ParametroInvalido(recurso, ["ano"], ["ano com 4 dígitos"])
        if periodo and not periodo.isdigit():
            raise ParametroInvalido(recurso, ["periodo"], ["número do período (ex: 1 = 1º trimestre)"])

        # sem ano/período, o listing da fonte diz qual é o mais novo QUE TEM o
        # tipo pedido, consórcio sai depois dos bancos, então pode ser preciso
        # recuar um período (ou um ano)
        lista = await self.get_json(RECLAMACOES_URL, timeout=30)
        anos = lista.get("anos", []) if isinstance(lista, dict) else []
        candidatos = [e for e in anos if not ano or str(e.get("ano")) == ano]
        if not candidatos:
            raise ParametroInvalido(recurso, ["ano"], sorted(str(a.get("ano")) for a in anos))

        def periodos_com_tipo(entrada: dict):
            periodicidades = {p.get("periodicidade"): p for p in entrada.get("periodicidades", [])}
            for nome in ("TRIMESTRAL", "SEMESTRAL", "ANUAL", "MENSAL", "BIMESTRAL"):
                per = periodicidades.get(nome)
                if not per:
                    continue
                nums = [
                    int(x.get("periodo"))
                    for x in per.get("periodos", [])
                    if any(tp.get("tipo") == TIPOS_RECLAMACOES[tipo] for tp in x.get("tipos", []))
                ]
                if nums:
                    return per, nums
            return None, []

        per, disponiveis, alvo = None, [], None
        for entrada in reversed(candidatos):  # do ano mais novo pro mais velho
            per, disponiveis = periodos_com_tipo(entrada)
            if disponiveis:
                alvo = entrada
                break
        if alvo is None or per is None:
            raise ParametroInvalido(recurso, ["tipo"], ["sem ranking publicado pra esse tipo/ano"])
        ano = str(alvo.get("ano"))
        if periodo and int(periodo) not in disponiveis:
            raise ParametroInvalido(recurso, ["periodo"], [str(p) for p in sorted(disponiveis)])
        periodo = int(periodo) if periodo else max(disponiveis)

        resp = await self._request(
            "GET",
            f"{RECLAMACOES_URL}/arquivo",
            params={
                "ano": ano,
                "periodicidade": per.get("periodicidade"),
                "periodo": periodo,
                "tipo": TIPOS_RECLAMACOES[tipo],
            },
            timeout=50,
        )
        texto = resp.content.decode("latin-1")
        leitor = csv.DictReader(io.StringIO(texto), delimiter=";")
        # bancos e consórcios falam dialetos diferentes: "Instituição
        # financeira" vs "Administradora de consórcio", "reclamações
        # procedentes" vs "reclamações reguladas procedentes", e o CSV de
        # consórcio nem tem a coluna Categoria (o ranking é um só)
        col = {}
        for nome in leitor.fieldnames or []:
            n = (nome or "").casefold()
            if n.startswith("instituição") or n.startswith("administradora"):
                col["instituicao"] = nome
            elif n.startswith("índice"):
                col["indice"] = nome
            elif n.startswith("categoria"):
                col["categoria"] = nome
            elif n.startswith("quantidade total de reclamações respondidas"):
                col["respondidas"] = nome
            elif "procedentes extrapoladas" in n or "reguladas - outras" in n:
                pass  # estimativa e miscelânea; ficam de fora
            elif n.startswith("quantidade de reclamações reguladas procedentes") or n.startswith(
                "quantidade de reclamações procedentes"
            ):
                col["procedentes"] = nome
            elif n.startswith("quantidade total de reclamações analisadas"):
                col["analisadas"] = nome
            elif "clientes" in n and "quantidade" in n and "clientes" not in str(col.get("clientes", "")).casefold():
                col.setdefault("clientes", nome)

        def inteiro(linha: dict, chave: str) -> int | None:
            bruto = (linha.get(col.get(chave, ""), "") or "").strip()
            return int(bruto) if bruto.isdigit() else None

        rotulo = ROTULO_PERIODO.get(per.get("periodicidade"), "período")
        etiqueta = f"{periodo}º {rotulo} de {ano}"
        itens = []
        for linha in leitor:
            nome = limpa_texto(linha.get(col.get("instituicao", ""), ""))
            if not nome:
                continue
            indice = valor_br(linha.get(col.get("indice", ""), ""))
            categoria = linha.get(col.get("categoria", ""), "") or ""
            # sem coluna Categoria (consórcios) o ranking é um só: todo mundo
            # com índice entra na fila
            itens.append(
                RankingReclamacao(
                    instituicao=nome.replace(" (conglomerado)", ""),
                    indice=float(indice) if indice is not None else None,
                    top15=categoria.strip().startswith("Top") if "categoria" in col else True,
                    reclamacoes_procedentes=inteiro(linha, "procedentes"),
                    reclamacoes_respondidas=inteiro(linha, "respondidas"),
                    reclamacoes_analisadas=inteiro(linha, "analisadas"),
                    clientes=inteiro(linha, "clientes"),
                    periodo=etiqueta,
                ).model_dump(mode="json")
            )
        # o ranking OFICIAL é o Top 15 (instituições grandes): posição só vale
        # lá dentro, comparar índice de banco de 400 clientes com o do Itaú
        # seria estatística de mentira
        itens.sort(key=lambda i: (not i["top15"], i["indice"] is None, -(i["indice"] or 0)))
        pos = 0
        for item in itens:
            if item["top15"] and item["indice"] is not None:
                pos += 1
                item["posicao"] = pos
        grupo = str(params.get("grupo", "todos")).lower()
        if grupo not in {"todos", "top15"}:
            raise ParametroInvalido(recurso, ["grupo"], ["todos", "top15"])
        if grupo == "top15":
            itens = [i for i in itens if i["top15"]]
        if busca:
            itens = [i for i in itens if busca in i["instituicao"].casefold()]
        total_disponivel = len(itens)
        itens = itens[: int(limit)]

        meta = {
            "ano": int(ano),
            "periodo": periodo,
            "periodicidade": per.get("periodicidade"),
            "tipo": tipo,
            "instituicoes_no_ranking": total_disponivel,
            "fonte": FONTE_RECLAMACOES,
        }
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=itens, total=len(itens), meta=meta
        )
