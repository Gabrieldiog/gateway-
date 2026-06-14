import re
from decimal import Decimal, InvalidOperation
from typing import Any

from pydantic import ValidationError

from balcao.connectors.base import BaseConnector, NormalizedResponse, register
from balcao.exceptions import ParametroInvalido, RecursoNaoEncontrado
from balcao.models import DespesaFuncao, FinancaEstado
from balcao.normalize import normaliza_uf

# código IBGE de 2 dígitos de cada ente estadual (constitucional, não muda)
UF_IBGE = {
    "RO": 11, "AC": 12, "AM": 13, "RR": 14, "PA": 15, "AP": 16, "TO": 17,
    "MA": 21, "PI": 22, "CE": 23, "RN": 24, "PB": 25, "PE": 26, "AL": 27,
    "SE": 28, "BA": 29, "MG": 31, "ES": 32, "RJ": 33, "SP": 35, "PR": 41,
    "SC": 42, "RS": 43, "MS": 50, "MT": 51, "GO": 52, "DF": 53,
}

# linha de função de 1º nível no DCA: "10 - Saúde" (subfunção vem como "10.301 - ...")
FUNCAO = re.compile(r"^\d{2} - ")
ANO_PADRAO = 2023
# o SICONFI responde devagar e manda relatórios grandes
TIMEOUT = 45.0


@register
class TesouroConnector(BaseConnector):
    name = "tesouro"
    base_url = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt"
    description = "Tesouro Nacional (SICONFI): receita, arrecadação de impostos e despesa por função dos estados"
    resources = {
        "estados/{uf}": "receita total, quanto vem de impostos e despesa total do estado num ano",
        "estados/{uf}/despesas": "despesa por função — onde o estado gasta (saúde, educação, segurança...)",
    }

    async def fetch(self, recurso: str, **params: Any) -> NormalizedResponse:
        partes = [p for p in recurso.strip("/").split("/") if p]
        match partes:
            case ["estados", uf]:
                return await self._panorama(recurso, uf, params)
            case ["estados", uf, "despesas"]:
                return await self._despesas(recurso, uf, params)
            case _:
                raise RecursoNaoEncontrado(self.name, recurso, sorted(self.resources))

    def _ente(self, recurso: str, uf: str) -> tuple[str, int]:
        sigla = normaliza_uf(uf)
        cod = UF_IBGE.get(sigla) if sigla else None
        if cod is None:
            raise ParametroInvalido(recurso, [f"uf={uf}"], sorted(UF_IBGE))
        return sigla, cod

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

    async def _panorama(self, recurso: str, uf: str, params: dict) -> NormalizedResponse:
        sigla, cod = self._ente(recurso, uf)
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

        pop = next((i.get("populacao") for i in receitas + despesas if i.get("populacao")), None)
        fin = FinancaEstado(
            uf=sigla,
            ano=ano,
            populacao=int(float(pop)) if pop else None,
            receita_total=receita_total or Decimal(0),
            receita_impostos=impostos,
            despesa_total=despesa_total or Decimal(0),
        )
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=[fin.model_dump(mode="json")], total=1, meta={"ano": ano}
        )

    async def _despesas(self, recurso: str, uf: str, params: dict) -> NormalizedResponse:
        sigla, cod = self._ente(recurso, uf)
        ano = self._ano(recurso, params)
        itens = await self._dca("DCA-Anexo I-E", ano, cod)

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
                    DespesaFuncao(uf=sigla, ano=ano, funcao=nome, valor=valor).model_dump(mode="json")
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
