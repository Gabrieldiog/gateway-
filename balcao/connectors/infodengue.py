"""InfoDengue (Fiocruz/FGV): alerta de dengue, zika e chikungunya por
município, semana a semana. A fonte devolve o ano inteiro com nowcasting —
as semanas recentes são estimativa de modelo, não contagem fechada — e
datas em epoch de milissegundos. O conector traduz tudo pro schema comum."""

from datetime import date, datetime, timezone
from typing import Any

from balcao.connectors.base import BaseConnector, NormalizedResponse, register
from balcao.exceptions import ParametroInvalido, RecursoNaoEncontrado
from balcao.models import AlertaDengue
from balcao.normalize import so_digitos

DOENCAS = {"dengue", "zika", "chikungunya"}
NIVEIS = {1: "verde", 2: "amarelo", 3: "laranja", 4: "vermelho"}

PARAMS = {"municipio", "doenca", "ano"}

FONTE = {
    "nome": "InfoDengue — Fiocruz / FGV",
    "url": "https://info.dengue.mat.br",
    "nota": (
        "Alerta semanal por município. 'Casos estimados' é nowcasting: o modelo "
        "corrige o atraso de notificação, então as semanas recentes mudam a cada "
        "atualização. O nível vai de verde (1) a vermelho (4)."
    ),
}


@register
class InfodengueConnector(BaseConnector):
    name = "infodengue"
    base_url = "https://info.dengue.mat.br/api"
    description = "InfoDengue (Fiocruz): dengue, zika e chikungunya por município, com nível de alerta semanal"
    resources = {
        "alertas": "semanas epidemiológicas de um município (params: municipio = código IBGE, doenca = dengue|zika|chikungunya, ano)",
    }

    async def fetch(self, recurso: str, **params: Any) -> NormalizedResponse:
        partes = [p for p in recurso.strip("/").split("/") if p]
        match partes:
            case ["alertas"] | ["alertcity"]:
                return await self._alertas(recurso, params)
            case _:
                raise RecursoNaoEncontrado(self.name, recurso, sorted(self.resources))

    async def _alertas(self, recurso: str, params: dict) -> NormalizedResponse:
        invalidos = sorted(set(params) - PARAMS)
        if invalidos:
            raise ParametroInvalido(recurso, invalidos, sorted(PARAMS))

        ibge = so_digitos(str(params.get("municipio", "")))
        if not ibge or len(ibge) != 7:
            raise ParametroInvalido(recurso, ["municipio"], ["municipio = código IBGE de 7 dígitos"])
        doenca = str(params.get("doenca", "dengue")).lower()
        if doenca not in DOENCAS:
            raise ParametroInvalido(recurso, ["doenca"], sorted(DOENCAS))
        ano = params.get("ano", date.today().year)
        if not str(ano).isdigit():
            raise ParametroInvalido(recurso, ["ano"], ["ano com 4 dígitos"])

        bruto = await self.get_json(
            "/alertcity",
            params={
                "geocode": ibge,
                "disease": doenca,
                "format": "json",
                "ew_start": 1,
                "ew_end": 53,
                "ey_start": int(ano),
                "ey_end": int(ano),
            },
            timeout=30,
        )

        itens = []
        for r in bruto if isinstance(bruto, list) else []:
            nivel = int(r.get("nivel") or 0)
            itens.append(
                AlertaDengue(
                    municipio=str(r.get("municipio_nome") or ""),
                    ibge=int(ibge),
                    doenca=doenca,
                    semana=int(r.get("SE") or 0),
                    inicio_semana=_epoch_ms(r.get("data_iniSE")),
                    casos=r.get("casos"),
                    casos_estimados=r.get("casos_est"),
                    incidencia_100k=r.get("p_inc100k"),
                    rt=r.get("Rt"),
                    nivel=nivel,
                    alerta=NIVEIS.get(nivel, "desconhecido"),
                    populacao=int(r["pop"]) if r.get("pop") else None,
                ).model_dump(mode="json")
            )
        # a fonte manda da semana mais recente pra mais antiga; mantém assim
        meta = {"municipio": ibge, "doenca": doenca, "ano": int(ano), "fonte": FONTE}
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=itens, total=len(itens), meta=meta
        )


def _epoch_ms(valor: Any) -> date | None:
    # a fonte manda o início da semana como epoch em MILissegundos
    try:
        return datetime.fromtimestamp(int(valor) / 1000, tz=timezone.utc).date()
    except (TypeError, ValueError, OSError):
        return None
