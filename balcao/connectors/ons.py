"""ONS (Operador Nacional do Sistema Elétrico): geração de energia do SIN
quase em tempo real. O endpoint BalancoEnergetico devolve o dia inteiro
minuto a minuto, a gente pega o último instante válido e soma os quatro
subsistemas pra montar o total do Brasil (o SIN), com o mix por fonte e o
percentual renovável. Fonte "tempo real": não cacheia."""

from typing import Any

from balcao.connectors.base import BaseConnector, NormalizedResponse, register
from balcao.exceptions import ErroUpstream, RecursoNaoEncontrado
from balcao.models import GeracaoEnergia

# chave no JSON do ONS -> nome legível do subsistema
SUBSISTEMAS = {
    "sudesteECentroOeste": "Sudeste/Centro-Oeste",
    "sul": "Sul",
    "nordeste": "Nordeste",
    "norte": "Norte",
}

FONTES = ("hidraulica", "termica", "eolica", "solar", "nuclear")

FONTE = {
    "nome": "ONS, Operador Nacional do Sistema Elétrico",
    "url": "https://www.ons.org.br/paginas/energia-agora/carga-e-geracao",
    "nota": (
        "Geração verificada do Sistema Interligado Nacional, atualizada a cada "
        "minuto pelos sistemas de tempo real do ONS. Itaipu entra como hidráulica. "
        "'Renovável' soma hidráulica, eólica e solar."
    ),
}


@register
class OnsConnector(BaseConnector):
    name = "ons"
    base_url = "https://tr.ons.org.br/Content/Get"
    description = "ONS: geração do SIN por fonte quase em tempo real (hidráulica, eólica, solar, térmica) e carga"
    # tempo real: o valor muda a cada minuto, então não passa pelo cache
    cacheavel = False
    resources = {
        "geracao": "geração do SIN agora: mix por fonte, carga e % renovável (atualiza a cada minuto)",
    }

    async def fetch(self, recurso: str, **params: Any) -> NormalizedResponse:
        partes = [p for p in recurso.strip("/").split("/") if p]
        match partes:
            case ["geracao"] | ["agora"]:
                return await self._geracao(recurso)
            case _:
                raise RecursoNaoEncontrado(self.name, recurso, sorted(self.resources))

    async def _geracao(self, recurso: str) -> NormalizedResponse:
        bruto = await self.get_json("/BalancoEnergetico")
        if not isinstance(bruto, list) or not bruto:
            raise ErroUpstream(self.name)

        ponto = self._ultimo_valido(bruto)
        if ponto is None:
            raise ErroUpstream(self.name)

        instante = str(ponto.get("Data", ""))
        sin = {f: 0.0 for f in FONTES}
        carga_sin = 0.0
        regioes: list[dict] = []
        for chave, nome in SUBSISTEMAS.items():
            bloco = ponto.get(chave) or {}
            g = bloco.get("geracao") or {}
            vals = {f: _num(g.get(f)) for f in FONTES}
            # Itaipu vem em campos próprios no SE/CO; conta como hidráulica
            vals["hidraulica"] += _num(g.get("itaipu50HzBrasil")) + _num(g.get("itaipu60Hz"))
            cv = _num(bloco.get("cargaVerificada"))
            for f in FONTES:
                sin[f] += vals[f]
            carga_sin += cv
            regioes.append(self._linha(instante, nome, vals, cv))

        linha_sin = self._linha(instante, "SIN", sin, carga_sin)
        dados = [linha_sin, *regioes]
        meta = {"instante": instante, "tempo_real": True, "fonte": FONTE}
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=dados, total=len(dados), meta=meta
        )

    @staticmethod
    def _ultimo_valido(pontos: list) -> dict | None:
        # o ONS já publica o minuto seguinte com zeros; volta do fim até achar
        # um instante com geração de verdade no maior subsistema (SE/CO)
        for ponto in reversed(pontos):
            if not isinstance(ponto, dict):
                continue
            g = (ponto.get("sudesteECentroOeste") or {}).get("geracao") or {}
            if _num(g.get("total")) > 0 or _num(g.get("hidraulica")) > 0:
                return ponto
        return None

    @staticmethod
    def _linha(instante: str, regiao: str, vals: dict, carga: float) -> dict:
        total = sum(vals.values())
        renovavel = vals["hidraulica"] + vals["eolica"] + vals["solar"]
        return GeracaoEnergia(
            instante=instante,
            regiao=regiao,
            geracao_total=round(total, 1),
            hidraulica=round(vals["hidraulica"], 1),
            termica=round(vals["termica"], 1),
            eolica=round(vals["eolica"], 1),
            solar=round(vals["solar"], 1),
            nuclear=round(vals["nuclear"], 1),
            carga=round(carga, 1) if carga else None,
            renovavel_pct=round(100 * renovavel / total, 1) if total else None,
        ).model_dump(mode="json")


def _num(valor: Any) -> float:
    try:
        return float(valor)
    except (TypeError, ValueError):
        return 0.0
