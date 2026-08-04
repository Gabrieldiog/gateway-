"""Cotações de câmbio, ouro e cripto.

A fonte preferida é a AwesomeAPI: preço de mercado de segundo a segundo, tudo
num request só. O problema é que ela cobra cadastro e barra IP de datacenter
(429), que é justamente onde o gateway roda. Depender só dela já derrubou o
caderno Pulso três vezes.

Então o token virou atalho, não requisito: quando ele falta ou a AwesomeAPI
recusa, entra o plano B, montado só com fontes abertas e sem cadastro:

    câmbio  Frankfurter, que republica a taxa de referência do Banco Central
            Europeu (uma vez por dia útil, não é tempo real e a resposta diz)
    ouro    gold-api, preço da onça troy em dólar, convertido pelo câmbio acima
    cripto  Binance, preço à vista dos pares em real

Cada cotação carrega a origem e se é ao vivo: numa página que se apoia em
dizer de onde veio o dado, trocar de fonte em silêncio seria pior que o erro.
"""

import json
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from zoneinfo import ZoneInfo

from pydantic import ValidationError

from balcao.config import get_settings
from balcao.connectors.base import BaseConnector, NormalizedResponse, register
from balcao.exceptions import ErroUpstream, ParametroInvalido, RecursoNaoEncontrado
from balcao.models import Cotacao
from balcao.resilience import CircuitBreaker

# um ou mais pares separados por vírgula: USD-BRL,EUR-BRL,BTC-BRL
PARES = re.compile(r"^[A-Za-z]{3,4}-[A-Za-z]{3,4}(,[A-Za-z]{3,4}-[A-Za-z]{3,4})*$")

FRANKFURTER = "https://api.frankfurter.dev/v1"
GOLD_API = "https://api.gold-api.com/price"
BINANCE = "https://api.binance.com/api/v3/ticker/24hr"

# as moedas que o BCE publica e o Frankfurter repassa
MOEDAS_BCE = frozenset(
    "AUD BGN BRL CAD CHF CNY CZK DKK EUR GBP HKD HUF IDR ILS INR ISK JPY KRW "
    "MXN MYR NOK NZD PHP PLN RON SEK SGD THB TRY USD ZAR".split()
)
METAIS = {"XAU": "Ouro", "XAG": "Prata"}

# a AwesomeAPI manda o nome pronto ("Dólar Americano/Real Brasileiro"); no
# plano B o nome se monta aqui, pra tela não virar uma parede de siglas
NOMES = {
    "USD": "Dólar Americano", "EUR": "Euro", "GBP": "Libra Esterlina",
    "CHF": "Franco Suíço", "JPY": "Iene Japonês", "CAD": "Dólar Canadense",
    "AUD": "Dólar Australiano", "CNY": "Yuan Chinês", "ARS": "Peso Argentino",
    "BRL": "Real Brasileiro", "XAU": "Ouro", "XAG": "Prata",
    "BTC": "Bitcoin", "ETH": "Ethereum", "SOL": "Solana", "USDT": "Tether",
    "XRP": "XRP", "ADA": "Cardano", "DOGE": "Dogecoin", "BNB": "BNB",
}

SAO_PAULO = ZoneInfo("America/Sao_Paulo")
# a AwesomeAPI é o caminho feliz, mas não pode segurar a página: estourou o
# tempo, o plano B assume. O cache de vida curta absorve o custo do polling.
TIMEOUT_PRINCIPAL = 6.0


def _quantiza(valor: Decimal) -> Decimal:
    """Seis casas seguram tanto o iene quanto o bitcoin sem virar dízima."""
    return valor.quantize(Decimal("0.000001")).normalize()


def _variacao(agora: Decimal, antes: Decimal) -> float | None:
    if not antes:
        return None
    return round(float((agora - antes) / antes * 100), 2)


def _nome(par: tuple[str, str]) -> str:
    code, codein = par
    return f"{NOMES.get(code, code)}/{NOMES.get(codein, codein)}"


@register
class CotacoesConnector(BaseConnector):
    name = "cotacoes"
    base_url = "https://economia.awesomeapi.com.br/json"
    description = (
        "Cotações de câmbio, ouro e cripto (preço de mercado), pela AwesomeAPI "
        "com plano B em fontes abertas (Frankfurter/BCE, gold-api e Binance)"
    )
    # o token da AwesomeAPI é opcional: melhora a cota, mas a falta dele não
    # pode tirar o caderno do ar; é pra isso que existe o plano B
    requires_key = False
    # cache curto (cache_vivo_ttl): o /pulso faz polling, então um cache de
    # segundos segura as fontes. O valor ainda é "ao vivo" pro leitor.
    tempo_real = True
    resources = {
        "last/{pares}": "cotação atual de um ou mais pares, ex: USD-BRL,EUR-BRL,BTC-BRL",
    }

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        # o breaker herdado cuida da AwesomeAPI; o plano B tem o seu, senão a
        # fonte principal caída fecharia a porta das abertas junto
        self._breaker_livre = CircuitBreaker(
            self.breaker.limite_falhas, self.breaker.cooldown
        )

    async def fetch(self, recurso: str, **params: Any) -> NormalizedResponse:
        partes = [p for p in recurso.strip("/").split("/") if p]
        match partes:
            case ["last", pares]:
                return await self._last(recurso, pares)
            case _:
                raise RecursoNaoEncontrado(self.name, recurso, sorted(self.resources))

    async def _last(self, recurso: str, pares: str) -> NormalizedResponse:
        if not PARES.match(pares):
            raise ParametroInvalido(recurso, [f"pares={pares}"], ["ex: USD-BRL,EUR-BRL,BTC-BRL"])
        pedidos = []
        for bruto in pares.upper().split(","):
            code, _, codein = bruto.partition("-")
            if (code, codein) not in pedidos:
                pedidos.append((code, codein))

        falha: ErroUpstream | None = None
        try:
            cotacoes = await self._awesomeapi(pares)
        except ErroUpstream as exc:
            falha, cotacoes = exc, []

        plano_b = not cotacoes
        if plano_b:
            cotacoes, falha = await self._plano_b(pedidos, falha)
        if not cotacoes:
            # nenhuma fonte de pé: dizer que a fonte caiu é mais honesto que
            # devolver lista vazia, como se o dólar não existisse hoje
            raise falha or ErroUpstream(self.name)

        return NormalizedResponse(
            fonte=self.name,
            recurso=recurso,
            dados=[c.model_dump(mode="json") for c in cotacoes],
            total=len(cotacoes),
            meta={
                "plano_b": plano_b,
                "origens": sorted({c.origem for c in cotacoes}),
            },
        )

    # --- plano A: AwesomeAPI ------------------------------------------------

    async def _awesomeapi(self, pares: str) -> list[Cotacao]:
        # o token (cadastro grátis) dá 100 mil/mês e cota própria; sem ele a
        # fonte atende no limite anônimo e barra IP de datacenter
        token = get_settings().awesomeapi_token
        bruto = await self.get_json(
            f"/last/{pares.upper()}",
            params={"token": token} if token else None,
            timeout=TIMEOUT_PRINCIPAL,
        )
        cotacoes: list[Cotacao] = []
        # a AwesomeAPI devolve um dict {"USDBRL": {...}, "EURBRL": {...}}
        for v in (bruto or {}).values():
            try:
                cotacoes.append(self._norm(v))
            except (ValidationError, InvalidOperation, KeyError, TypeError):
                continue
        return cotacoes

    @staticmethod
    def _norm(v: dict) -> Cotacao:
        def dec(x: Any) -> Decimal | None:
            return Decimal(str(x)) if x not in (None, "") else None

        return Cotacao(
            par=f"{v['code']}/{v['codein']}",
            moeda=v["code"],
            nome=v.get("name"),
            compra=Decimal(str(v["bid"])),
            venda=dec(v.get("ask")),
            variacao_pct=float(v["pctChange"]) if v.get("pctChange") not in (None, "") else None,
            maxima=dec(v.get("high")),
            minima=dec(v.get("low")),
            atualizado=v.get("create_date"),
            origem="awesomeapi",
            ao_vivo=True,
        )

    # --- plano B: só fontes abertas ----------------------------------------

    async def _plano_b(
        self, pedidos: list[tuple[str, str]], falha: ErroUpstream | None
    ) -> tuple[list[Cotacao], ErroUpstream | None]:
        """Divide os pares entre as três fontes livres. Cada uma responde por
        si: uma fora do ar não leva as outras junto, e o que der certo vai pra
        tela, meia página de verdade vale mais que uma página de erro."""
        cambio = [p for p in pedidos if p[0] in MOEDAS_BCE and p[1] in MOEDAS_BCE]
        ouro = [p for p in pedidos if p[0] in METAIS and p[1] in MOEDAS_BCE]
        cripto = [p for p in pedidos if p[0] not in MOEDAS_BCE and p[0] not in METAIS]

        # o metal vem cotado em dólar, então a conversão precisa do câmbio na
        # mesma moeda de destino
        precisa: dict[str, set[str]] = {}
        for code, codein in cambio:
            precisa.setdefault(codein, set()).add(code)
        for _, codein in ouro:
            precisa.setdefault(codein, set()).add("USD")

        taxas: dict[str, dict[str, tuple[Decimal, Decimal, str]]] = {}
        for base, moedas in precisa.items():
            try:
                taxas[base] = await self._frankfurter(base, sorted(moedas - {base}))
            except ErroUpstream as exc:
                falha, taxas[base] = exc, {}

        cotacoes: list[Cotacao] = []
        cotacoes += self._do_cambio(cambio, taxas)
        novas, falha = await self._do_ouro(ouro, taxas, falha)
        cotacoes += novas
        novas, falha = await self._da_binance(cripto, falha)
        cotacoes += novas

        ordem = {par: i for i, par in enumerate(pedidos)}
        cotacoes.sort(key=lambda c: ordem.get(tuple(c.par.split("/")), len(ordem)))
        return cotacoes, falha

    async def _frankfurter(
        self, base: str, moedas: list[str]
    ) -> dict[str, tuple[Decimal, Decimal, str]]:
        """Dois dias úteis de taxa numa tacada: o mais novo é o preço, o
        anterior serve pra calcular a variação que a tela mostra."""
        if not moedas:
            return {}
        bruto = await self.get_json(
            # janela aberta (10 dias atrás em diante) porque feriado e fim de
            # semana não publicam; a fonte devolve só os dias que existem
            f"{FRANKFURTER}/{self._dias_atras(10)}..",
            params={"base": base, "symbols": ",".join(moedas)},
            breaker=self._breaker_livre,
        )
        por_dia = (bruto or {}).get("rates") or {}
        dias = sorted(por_dia)
        if not dias:
            raise ErroUpstream(self.name)
        hoje, ontem = dias[-1], dias[-2] if len(dias) > 1 else dias[-1]
        saida = {}
        for moeda in moedas:
            atual, anterior = por_dia[hoje].get(moeda), por_dia[ontem].get(moeda)
            if atual:
                saida[moeda] = (
                    Decimal(str(atual)),
                    Decimal(str(anterior or atual)),
                    hoje,
                )
        return saida

    @staticmethod
    def _dias_atras(dias: int) -> str:
        hoje = datetime.now(SAO_PAULO).date()
        return str(hoje.replace(day=1) if hoje.day <= dias else hoje.replace(day=hoje.day - dias))

    def _do_cambio(
        self, pares: list[tuple[str, str]], taxas: dict[str, dict]
    ) -> list[Cotacao]:
        cotacoes = []
        for code, codein in pares:
            achado = taxas.get(codein, {}).get(code)
            if not achado:
                continue
            agora, antes, dia = achado
            # o Frankfurter cota "quanto de X vale 1 real"; o par que a tela
            # mostra é o inverso, quantos reais vale 1 dólar
            preco, preco_antes = 1 / agora, 1 / antes
            cotacoes.append(
                Cotacao(
                    par=f"{code}/{codein}",
                    moeda=code,
                    nome=_nome((code, codein)),
                    compra=_quantiza(preco),
                    variacao_pct=_variacao(preco, preco_antes),
                    atualizado=dia,
                    origem="frankfurter",
                    # taxa de referência do BCE, publicada uma vez por dia útil
                    ao_vivo=False,
                )
            )
        return cotacoes

    async def _do_ouro(
        self,
        pares: list[tuple[str, str]],
        taxas: dict[str, dict],
        falha: ErroUpstream | None,
    ) -> tuple[list[Cotacao], ErroUpstream | None]:
        cotacoes = []
        for code, codein in pares:
            fator = Decimal(1)
            if codein != "USD":
                achado = taxas.get(codein, {}).get("USD")
                if not achado:
                    continue
                fator = 1 / achado[0]
            try:
                bruto = await self.get_json(
                    f"{GOLD_API}/{code}", breaker=self._breaker_livre
                )
            except ErroUpstream as exc:
                falha = exc
                continue
            preco = (bruto or {}).get("price")
            if not preco:
                continue
            cotacoes.append(
                Cotacao(
                    par=f"{code}/{codein}",
                    moeda=code,
                    nome=f"{METAIS.get(code, code)} (onça troy)/{NOMES.get(codein, codein)}",
                    compra=_quantiza(Decimal(str(preco)) * fator),
                    atualizado=self._hora_local(bruto.get("updatedAt")),
                    origem="gold-api",
                    ao_vivo=True,
                )
            )
        return cotacoes, falha

    async def _da_binance(
        self, pares: list[tuple[str, str]], falha: ErroUpstream | None
    ) -> tuple[list[Cotacao], ErroUpstream | None]:
        if not pares:
            return [], falha
        simbolos = [f"{code}{codein}" for code, codein in pares]
        try:
            bruto = await self.get_json(
                BINANCE,
                # a Binance quer o lote como array JSON, sem espaço nenhum
                params={"symbols": json.dumps(simbolos, separators=(",", ":"))},
                breaker=self._breaker_livre,
            )
        except ErroUpstream as exc:
            # a Binance recusa o lote inteiro se um símbolo não existir; sem
            # cripto o resto da página segue de pé
            return [], exc
        de_par = {f"{code}{codein}": (code, codein) for code, codein in pares}
        cotacoes = []
        for t in bruto or []:
            par = de_par.get(t.get("symbol", ""))
            if not par or not t.get("lastPrice"):
                continue
            code, codein = par
            try:
                cotacoes.append(
                    Cotacao(
                        par=f"{code}/{codein}",
                        moeda=code,
                        nome=_nome(par),
                        compra=_quantiza(Decimal(str(t["lastPrice"]))),
                        venda=_quantiza(Decimal(str(t["askPrice"]))) if t.get("askPrice") else None,
                        variacao_pct=round(float(t["priceChangePercent"]), 2)
                        if t.get("priceChangePercent") not in (None, "")
                        else None,
                        maxima=_quantiza(Decimal(str(t["highPrice"]))) if t.get("highPrice") else None,
                        minima=_quantiza(Decimal(str(t["lowPrice"]))) if t.get("lowPrice") else None,
                        atualizado=self._hora_local(t.get("closeTime")),
                        origem="binance",
                        ao_vivo=True,
                    )
                )
            except (ValidationError, InvalidOperation, KeyError, TypeError, ValueError):
                continue
        return cotacoes, falha

    @staticmethod
    def _hora_local(quando: Any) -> str | None:
        """Normaliza o carimbo pro mesmo formato da AwesomeAPI, no horário de
        Brasília: a tela lê a hora daí e o leitor está no Brasil."""
        if quando in (None, ""):
            return None
        try:
            if isinstance(quando, (int, float)):  # epoch em ms (Binance)
                momento = datetime.fromtimestamp(quando / 1000, SAO_PAULO)
            else:  # ISO com Z (gold-api)
                momento = datetime.fromisoformat(str(quando).replace("Z", "+00:00"))
                momento = momento.astimezone(SAO_PAULO)
        except (ValueError, OSError, OverflowError):
            return None
        return momento.strftime("%Y-%m-%d %H:%M:%S")
