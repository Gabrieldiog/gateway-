import asyncio
from decimal import Decimal, InvalidOperation
from typing import Any

from pydantic import ValidationError

from balcao.connectors.base import BaseConnector, NormalizedResponse, register
from balcao.exceptions import ErroUpstream, ParametroInvalido, RecursoNaoEncontrado
from balcao.models import IndicadorEconomico, PontoSerie, TaxaJurosBanco
from balcao.normalize import data_br, limpa_texto, para_data

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
    "nome": "Banco Central — Sistema Gerenciador de Séries (SGS)",
    "url": "https://www3.bcb.gov.br/sgspub/",
    "nota": (
        "IPCA, INPC e IGP-M são os índices oficiais de inflação; Selic, CDI e "
        "poupança medem o preço do dinheiro. Valor mais recente publicado pelo BC."
    ),
}

PARAMS_SERIE = {"data_inicio", "data_fim", "ultimos"}


@register
class BacenConnector(BaseConnector):
    name = "bacen"
    base_url = "https://api.bcb.gov.br/dados/serie"
    description = "Banco Central (SGS): Selic, CDI, IPCA, IGP-M, câmbio e mais de 190 séries econômicas"
    suporta_busca = True
    resources = {
        "inflacao": "painel de custo de vida: IPCA, IGP-M, INPC, Selic, CDI, poupança e dólar (valor mais recente)",
        "juros-bancos": "ranking oficial: quanto cada banco cobra numa modalidade de crédito (params: modalidade, limit)",
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
        é lenta — o cache do gateway segura o resto."""
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
                        instituicao=limpa_texto(r.get("InstituicaoFinanceira")) or "—",
                        modalidade=limpa_texto(r.get("Modalidade")) or "—",
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
                "nome": "Banco Central — ranking de taxas de juros (Olinda)",
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
