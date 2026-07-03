from typing import Any

from pydantic import ValidationError

from balcao.connectors.base import BaseConnector, NormalizedResponse, register
from balcao.exceptions import ParametroInvalido, RecursoNaoEncontrado
from balcao.models import IndicadorAgro
from balcao.normalize import normaliza_uf

# código IBGE de 2 dígitos de cada UF (o SIDRA usa no nível n3)
UF_IBGE = {
    "RO": 11, "AC": 12, "AM": 13, "RR": 14, "PA": 15, "AP": 16, "TO": 17,
    "MA": 21, "PI": 22, "CE": 23, "RN": 24, "PB": 25, "PE": 26, "AL": 27,
    "SE": 28, "BA": 29, "MG": 31, "ES": 32, "RJ": 33, "SP": 35, "PR": 41,
    "SC": 42, "RS": 43, "MS": 50, "MT": 51, "GO": 52, "DF": 53,
}

# PAM, tabela 1612 (lavouras temporárias), classificação 81 = produto
PRODUTOS = {
    "soja": 2713, "milho": 2711, "arroz": 2692, "feijao": 2702,
    "trigo": 2716, "algodao": 2689, "cana": 2696, "mandioca": 2708,
}
VARIAVEIS_PAM = {
    "quantidade": 214,    # quantidade produzida (toneladas)
    "area": 109,          # área plantada (hectares)
    "area_colhida": 216,  # área colhida (hectares)
    "valor": 215,         # valor da produção (mil reais)
    "rendimento": 112,    # rendimento médio (kg/ha)
}

# pecuária, tabela 3939, classificação 79 = tipo de rebanho; variável 105 = efetivo
REBANHOS = {
    "bovino": 2670, "suino": 32794, "galinaceos": 32796, "equino": 2672,
    "caprino": 2681, "ovino": 2677, "bubalino": 2675, "codorna": 2680,
}

@register
class SidraConnector(BaseConnector):
    name = "sidra"
    base_url = "https://apisidra.ibge.gov.br"
    description = "IBGE SIDRA: produção agrícola (PAM) e pecuária por estado e município"
    resources = {
        "producao": (
            "produção agrícola municipal (PAM); filtros: "
            f"produto ({', '.join(PRODUTOS)}), variavel ({', '.join(VARIAVEIS_PAM)}), uf, municipio, ano"
        ),
        "rebanho": (
            "efetivo dos rebanhos (pecuária); filtros: "
            f"animal ({', '.join(REBANHOS)}), uf, municipio, ano"
        ),
    }

    async def fetch(self, recurso: str, **params: Any) -> NormalizedResponse:
        partes = [p for p in recurso.strip("/").split("/") if p]
        match partes:
            case ["producao"]:
                return await self._consulta(
                    recurso, params, tabela=1612, classif=81, itens=PRODUTOS,
                    variaveis=VARIAVEIS_PAM, chave="produto", item_padrao="soja",
                    var_padrao="quantidade",
                )
            case ["rebanho"]:
                return await self._consulta(
                    recurso, params, tabela=3939, classif=79, itens=REBANHOS,
                    variaveis={"efetivo": 105}, chave="animal", item_padrao="bovino",
                    var_padrao="efetivo",
                )
            case _:
                raise RecursoNaoEncontrado(self.name, recurso, sorted(self.resources))

    async def _consulta(
        self, recurso, params, *, tabela, classif, itens, variaveis, chave, item_padrao, var_padrao
    ) -> NormalizedResponse:
        aceitos = {chave, "uf", "municipio", "ano"}
        if len(variaveis) > 1:
            aceitos.add("variavel")
        invalidos = sorted(set(params) - aceitos)
        if invalidos:
            raise ParametroInvalido(recurso, invalidos, sorted(aceitos))

        item = str(params.get(chave, item_padrao)).lower()
        if item not in itens:
            raise ParametroInvalido(recurso, [f"{chave}={item}"], sorted(itens))
        var = str(params.get("variavel", var_padrao)).lower()
        if var not in variaveis:
            raise ParametroInvalido(recurso, [f"variavel={var}"], sorted(variaveis))
        ano = str(params.get("ano", "")).strip()
        if ano and not ano.isdigit():
            raise ParametroInvalido(recurso, ["ano"], ["ano (AAAA) ou vazio pro mais recente"])
        # sem ano, o SIDRA resolve "last" pro ultimo periodo publicado — a
        # pagina nunca fica presa num ano que ja virou historia
        periodo = ano or "last"

        nivel = self._nivel(recurso, params)
        path = f"/values/t/{tabela}/{nivel}/v/{variaveis[var]}/p/{periodo}/c{classif}/{itens[item]}"
        bruto = await self.get_json(path)

        registros = self._parse(bruto, int(ano) if ano else None)
        ano_usado = registros[0]["ano"] if registros else (int(ano) if ano else None)
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=registros, total=len(registros),
            meta={"ano": ano_usado, "ano_automatico": not ano, chave: item, "variavel": var},
        )

    def _nivel(self, recurso: str, params: dict) -> str:
        if params.get("municipio"):
            mun = str(params["municipio"])
            if not mun.isdigit():
                raise ParametroInvalido(recurso, [f"municipio={mun}"], ["municipio (código IBGE)"])
            return f"n6/{mun}"
        if params.get("uf"):
            sigla = normaliza_uf(params["uf"])
            cod = UF_IBGE.get(sigla) if sigla else None
            if cod is None:
                raise ParametroInvalido(recurso, [f"uf={params['uf']}"], sorted(UF_IBGE))
            return f"n3/{cod}"
        return "n3/all"  # todas as UFs, pra comparar

    def _parse(self, bruto: Any, ano: int | None) -> list[dict]:
        # o SIDRA devolve uma lista cujo primeiro item é o cabeçalho (rótulos das
        # chaves crípticas); as chaves são posicionais: D1=localidade, D2=variável,
        # D3=ano, D4=item (produto/rebanho), V=valor, MN=unidade
        if not isinstance(bruto, list) or len(bruto) < 2:
            return []
        registros: list[dict] = []
        for row in bruto[1:]:
            try:
                reg = IndicadorAgro(
                    localidade=row.get("D1N") or "",
                    localidade_id=int(row["D1C"]) if str(row.get("D1C") or "").isdigit() else None,
                    # o ano de verdade vem em cada linha (D3C) — essencial no
                    # modo "last", em que nao sabemos o periodo de antemao
                    ano=int(row["D3C"]) if str(row.get("D3C") or "").isdigit() else ano,
                    item=row.get("D4N") or "",
                    variavel=row.get("D2N") or "",
                    valor=self._numero(row.get("V")),
                    unidade=row.get("MN") or None,
                )
            except (ValidationError, ValueError):
                continue
            registros.append(reg.model_dump(mode="json"))
        # maior primeiro; quem não tem dado (None) vai pro fim
        registros.sort(key=lambda r: (r["valor"] is None, -(r["valor"] or 0.0)))
        return registros

    @staticmethod
    def _numero(v: Any) -> float | None:
        # SIDRA usa "-", "..", "..." e "X" pra zero, sem dado e sigiloso
        if v is None:
            return None
        try:
            return float(str(v).strip())
        except ValueError:
            return None
