from decimal import Decimal, InvalidOperation
from typing import Any

from pydantic import ValidationError

from balcao.connectors.base import BaseConnector, NormalizedResponse, register
from balcao.exceptions import ParametroInvalido, RecursoNaoEncontrado
from balcao.models import PontoSerie
from balcao.normalize import data_br, para_data

# atalhos pros codigos de serie mais pedidos do SGS
SERIES = {
    "selic": 432,
    "cdi": 12,
    "ipca": 433,
    "igpm": 189,
    "dolar": 1,
    "euro": 21619,
}

PARAMS_SERIE = {"data_inicio", "data_fim", "ultimos"}


@register
class BacenConnector(BaseConnector):
    name = "bacen"
    base_url = "https://api.bcb.gov.br/dados/serie"
    description = "Banco Central (SGS): Selic, CDI, IPCA, IGP-M, câmbio e mais de 190 séries econômicas"
    suporta_busca = True
    resources = {
        "serie/{codigo}": f"pontos de uma série do SGS; filtros: {', '.join(sorted(PARAMS_SERIE))}",
        **{
            apelido: f"atalho pra série {codigo} do SGS"
            for apelido, codigo in SERIES.items()
        },
    }

    async def fetch(self, recurso: str, **params: Any) -> NormalizedResponse:
        partes = [p for p in recurso.strip("/").split("/") if p]
        match partes:
            case [apelido] if apelido in SERIES:
                return await self._serie(recurso, SERIES[apelido], params, nome=apelido)
            case ["serie", codigo] if codigo.isdigit():
                return await self._serie(recurso, int(codigo), params)
            case _:
                raise RecursoNaoEncontrado(self.name, recurso, sorted(self.resources))

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
