import re
from decimal import Decimal, InvalidOperation
from typing import Any

from pydantic import ValidationError

from balcao.connectors.base import BaseConnector, NormalizedResponse, register
from balcao.exceptions import ParametroInvalido, RecursoNaoEncontrado
from balcao.models import DespesaFuncao, FinancaEnte
from balcao.normalize import normaliza_uf

# código IBGE de 2 dígitos de cada ente estadual (constitucional, não muda)
UF_IBGE = {
    "RO": 11, "AC": 12, "AM": 13, "RR": 14, "PA": 15, "AP": 16, "TO": 17,
    "MA": 21, "PI": 22, "CE": 23, "RN": 24, "PB": 25, "PE": 26, "AL": 27,
    "SE": 28, "BA": 29, "MG": 31, "ES": 32, "RJ": 33, "SP": 35, "PR": 41,
    "SC": 42, "RS": 43, "MS": 50, "MT": 51, "GO": 52, "DF": 53,
}

# no SICONFI a União é o ente de id 1
UNIAO_ID = 1
# linha de função de 1º nível no DCA: "10 - Saúde" (subfunção vem como "10.301 - ...")
FUNCAO = re.compile(r"^\d{2} - ")
# "Prefeitura Municipal de Goiânia - GO" -> "Goiânia"
PREFEITURA = re.compile(r"^Prefeitura Municipal d[aeo]s?\s+")
SUFIXO_UF = re.compile(r"\s*-\s*[A-Z]{2}\s*$")
ANO_PADRAO = 2023
# o SICONFI responde devagar e manda relatórios grandes
TIMEOUT = 45.0


@register
class TesouroConnector(BaseConnector):
    name = "tesouro"
    base_url = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt"
    description = "Tesouro Nacional (SICONFI): receita, arrecadação de impostos e despesa por função da União, estados e municípios"
    resources = {
        "uniao": "receita total, quanto vem de impostos e despesa total da União num ano",
        "uniao/despesas": "despesa por função da União — onde o governo federal gasta",
        "estados/{uf}": "receita total, quanto vem de impostos e despesa total do estado num ano",
        "estados/{uf}/despesas": "despesa por função — onde o estado gasta (saúde, educação, segurança...)",
        "municipios/{ibge}": "receita total, impostos e despesa total de um município (código IBGE de 7 dígitos)",
        "municipios/{ibge}/despesas": "despesa por função de um município",
    }

    async def fetch(self, recurso: str, **params: Any) -> NormalizedResponse:
        partes = [p for p in recurso.strip("/").split("/") if p]
        match partes:
            case ["uniao"]:
                return await self._panorama(recurso, "uniao", UNIAO_ID, params)
            case ["uniao", "despesas"]:
                return await self._despesas(recurso, "uniao", UNIAO_ID, params)
            case ["estados", uf]:
                return await self._panorama(recurso, "estado", self._cod_uf(recurso, uf), params)
            case ["estados", uf, "despesas"]:
                return await self._despesas(recurso, "estado", self._cod_uf(recurso, uf), params)
            case ["municipios", ibge]:
                return await self._panorama(recurso, "municipio", self._cod_ibge(recurso, ibge), params)
            case ["municipios", ibge, "despesas"]:
                return await self._despesas(recurso, "municipio", self._cod_ibge(recurso, ibge), params)
            case _:
                raise RecursoNaoEncontrado(self.name, recurso, sorted(self.resources))

    def _cod_uf(self, recurso: str, uf: str) -> int:
        sigla = normaliza_uf(uf)
        cod = UF_IBGE.get(sigla) if sigla else None
        if cod is None:
            raise ParametroInvalido(recurso, [f"uf={uf}"], sorted(UF_IBGE))
        return cod

    def _cod_ibge(self, recurso: str, ibge: str) -> int:
        if not ibge.isdigit() or len(ibge) != 7:
            raise ParametroInvalido(recurso, [f"ibge={ibge}"], ["código IBGE de 7 dígitos do município"])
        return int(ibge)

    def _ano(self, recurso: str, params: dict) -> int:
        ano = str(params.get("ano", ANO_PADRAO))
        if not ano.isdigit():
            raise ParametroInvalido(recurso, ["ano"], ["ano"])
        return int(ano)

    async def _dca(self, anexo: str, ano: int, cod: int) -> list[dict]:
        bruto = await self.get_json(
            "/dca",
            params={"an_exercicio": ano, "no_anexo": anexo, "id_ente": cod},
            timeout=TIMEOUT,
        )
        return bruto.get("items", []) if isinstance(bruto, dict) else []

    @staticmethod
    def _identidade(nivel: str, cod: int, itens: list[dict]) -> dict:
        """Descobre quem é o ente a partir do que a fonte devolveu: nome,
        UF e população saem dos próprios itens do DCA."""
        inst = next((i.get("instituicao") for i in itens if i.get("instituicao")), None)
        uf = next((i.get("uf") for i in itens if i.get("uf")), None)
        pop = next((i.get("populacao") for i in itens if i.get("populacao")), None)
        if nivel == "uniao":
            # população não faz sentido pra União, e o DCA traz lixo nessa linha
            ente, uf, ibge, pop = "Brasil", None, None, None
        elif nivel == "estado":
            ente, ibge = uf or str(cod), cod
        else:
            limpo = SUFIXO_UF.sub("", inst or "").strip()
            ente = PREFEITURA.sub("", limpo).strip() or str(cod)
            ibge = cod
        return {
            "nivel": nivel,
            "ente": ente,
            "uf": uf,
            "ibge": ibge,
            "populacao": int(float(pop)) if pop else None,
        }

    async def _panorama(self, recurso: str, nivel: str, cod: int, params: dict) -> NormalizedResponse:
        ano = self._ano(recurso, params)
        receitas = await self._dca("DCA-Anexo I-C", ano, cod)
        despesas = await self._dca("DCA-Anexo I-E", ano, cod)

        receita_total = self._valor(receitas, "Receitas Brutas Realizadas", conta="TOTAL DAS RECEITAS")
        impostos = self._valor(receitas, "Receitas Brutas Realizadas", cod_conta="1.1.1.0.00.0.0")
        despesa_total = self._valor(despesas, "Despesas Empenhadas", conta="Despesas Exceto Intra")

        if receita_total is None and despesa_total is None:
            return NormalizedResponse(
                fonte=self.name, recurso=recurso, dados=[], total=0,
                meta={"ano": ano, "aviso": "o Tesouro não tem contas desse ente nesse ano"},
            )

        ident = self._identidade(nivel, cod, receitas + despesas)
        fin = FinancaEnte(
            **ident,
            ano=ano,
            receita_total=receita_total or Decimal(0),
            receita_impostos=impostos,
            despesa_total=despesa_total or Decimal(0),
        )
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=[fin.model_dump(mode="json")], total=1, meta={"ano": ano}
        )

    async def _despesas(self, recurso: str, nivel: str, cod: int, params: dict) -> NormalizedResponse:
        ano = self._ano(recurso, params)
        itens = await self._dca("DCA-Anexo I-E", ano, cod)
        ident = self._identidade(nivel, cod, itens)

        funcoes: list[dict] = []
        for i in itens:
            if i.get("coluna") != "Despesas Empenhadas":
                continue
            conta = (i.get("conta") or "").strip()
            if not FUNCAO.match(conta):  # só funções de 1º nível, sem subfunção
                continue
            try:
                valor = Decimal(str(i.get("valor") or "0"))
            except InvalidOperation:
                continue
            if valor <= 0:
                continue
            nome = conta.split(" - ", 1)[1] if " - " in conta else conta
            try:
                funcoes.append(
                    DespesaFuncao(**ident, ano=ano, funcao=nome, valor=valor).model_dump(mode="json")
                )
            except ValidationError:
                continue

        funcoes.sort(key=lambda d: Decimal(d["valor"]), reverse=True)
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=funcoes, total=len(funcoes), meta={"ano": ano}
        )

    @staticmethod
    def _valor(
        itens: list[dict], coluna: str, conta: str | None = None, cod_conta: str | None = None
    ) -> Decimal | None:
        for i in itens:
            if i.get("coluna") != coluna:
                continue
            # o cod_conta real vem com prefixo de rótulo (ex.: "RO1.1.1.0.00.0.0")
            if cod_conta and not (i.get("cod_conta") or "").endswith(cod_conta):
                continue
            if conta and conta not in (i.get("conta") or ""):
                continue
            try:
                return Decimal(str(i.get("valor")))
            except (InvalidOperation, TypeError):
                return None
        return None
