from typing import Any

from pydantic import ValidationError

from balcao.connectors.base import BaseConnector, NormalizedResponse, register
from balcao.exceptions import ParametroInvalido, RecursoNaoEncontrado
from balcao.models import Abate, IndicadorAgro, Leite, SafraMensal
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

# LSPA, tabela 6588 (safra em curso, estimativa mensal), classificação 48 —
# os códigos de produto NÃO são os mesmos da PAM
LSPA_PRODUTOS = {
    "soja": 39443, "milho1": 39441, "milho2": 39442, "arroz": 39432,
    "trigo": 39445, "cana": 39456, "cafe": 40527, "algodao": 39435,
    "banana": 39449, "laranja": 39463, "cebola": 39458,
}

# abate trimestral: uma tabela por bicho, mesma estrutura
ABATE_TABELAS = {"bovino": 1092, "suino": 1093, "frango": 1094}

# PAM municipal, tabela 5457, classificação 782 — terceiro mapa de códigos
PAM_MUNICIPAL = {"soja": 40124, "milho": 40122, "cafe": 40139, "cana": 40106}

FONTE = {
    "nome": "IBGE — SIDRA (PAM e PPM)",
    "url": "https://sidra.ibge.gov.br",
    "nota": "Produção Agrícola Municipal e Pesquisa da Pecuária Municipal, os censos anuais do campo.",
}

FONTE_LSPA = {
    "nome": "IBGE — LSPA (Levantamento Sistemático da Produção Agrícola)",
    "url": "https://sidra.ibge.gov.br/pesquisa/lspa",
    "nota": (
        "A estimativa oficial da safra em curso, revisada todo mês pelo IBGE. "
        "É previsão que amadurece: os números se ajustam a cada levantamento."
    ),
}

FONTE_TRIMESTRAIS = {
    "nome": "IBGE — pesquisas trimestrais do abate e do leite",
    "url": "https://sidra.ibge.gov.br/pesquisa/abate-de-animais",
    "nota": "Declaração obrigatória de frigoríficos e laticínios sob inspeção sanitária, consolidada por trimestre.",
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
        "safra": (
            "estimativa mensal da safra em curso (LSPA); filtros: "
            f"produto ({', '.join(LSPA_PRODUTOS)}), uf"
        ),
        "abate": f"abate trimestral; filtros: tipo ({', '.join(ABATE_TABELAS)})",
        "leite": "leite captado e preço médio pago ao produtor no trimestre; filtro: uf",
        "municipios": (
            "os municípios que mais produzem uma cultura numa UF (PAM 5457); "
            f"filtros: produto ({', '.join(PAM_MUNICIPAL)}), uf (obrigatória), limit"
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
            case ["safra"]:
                return await self._safra(recurso, params)
            case ["abate"]:
                return await self._abate(recurso, params)
            case ["leite"]:
                return await self._leite(recurso, params)
            case ["municipios"]:
                return await self._municipios(recurso, params)
            case _:
                raise RecursoNaoEncontrado(self.name, recurso, sorted(self.resources))

    async def _safra(self, recurso: str, params: dict) -> NormalizedResponse:
        """LSPA (tabela 6588): a estimativa mensal da safra em curso. O quirk
        da fonte: o item Total responde '..' — só produto especifico tem dado."""
        self._checa(recurso, params, {"produto", "uf"})
        produto = str(params.get("produto", "soja")).lower()
        if produto not in LSPA_PRODUTOS:
            raise ParametroInvalido(recurso, [f"produto={produto}"], sorted(LSPA_PRODUTOS))
        nivel = self._nivel(recurso, params) if params.get("uf") else "n1/all"
        path = f"/values/t/6588/{nivel}/v/35,109,36/p/last/c48/{LSPA_PRODUTOS[produto]}"
        bruto = await self.get_json(path)

        # as tres variaveis vem como linhas separadas; junta por localidade
        por_local: dict[str, dict] = {}
        mes = None
        for row in bruto[1:] if isinstance(bruto, list) else []:
            local = row.get("D1N") or "Brasil"
            mes = row.get("D3C") or mes
            reg = por_local.setdefault(local, {})
            valor = self._numero(row.get("V"))
            match row.get("D2C"):
                case "35":
                    reg["producao_t"] = valor
                case "109":
                    reg["area_plantada_ha"] = valor
                case "36":
                    reg["rendimento_kg_ha"] = valor
        itens = [
            SafraMensal(produto=produto, mes=mes or "", localidade=local, **campos).model_dump(mode="json")
            for local, campos in por_local.items()
        ]
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=itens, total=len(itens),
            meta={"produto": produto, "mes": mes, "fonte": FONTE_LSPA},
        )

    async def _abate(self, recurso: str, params: dict) -> NormalizedResponse:
        self._checa(recurso, params, {"tipo"})
        tipo = str(params.get("tipo", "bovino")).lower()
        if tipo not in ABATE_TABELAS:
            raise ParametroInvalido(recurso, [f"tipo={tipo}"], sorted(ABATE_TABELAS))
        bruto = await self.get_json(f"/values/t/{ABATE_TABELAS[tipo]}/n1/1/v/allxp/p/last")
        animais = peso = None
        trimestre = ""
        for row in bruto[1:] if isinstance(bruto, list) else []:
            trimestre = row.get("D3N") or trimestre
            if row.get("D2C") == "284":
                animais = self._numero(row.get("V"))
            elif row.get("D2C") == "285":
                peso = self._numero(row.get("V"))
        item = Abate(tipo=tipo, trimestre=trimestre, animais=animais, peso_kg=peso)
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=[item.model_dump(mode="json")], total=1,
            meta={"trimestre": trimestre, "fonte": FONTE_TRIMESTRAIS},
        )

    async def _leite(self, recurso: str, params: dict) -> NormalizedResponse:
        self._checa(recurso, params, {"uf"})
        nivel = self._nivel(recurso, params) if params.get("uf") else "n1/1"
        bruto = await self.get_json(f"/values/t/1086/{nivel}/v/282,2522/p/last")
        litros = preco = None
        trimestre = local = ""
        for row in bruto[1:] if isinstance(bruto, list) else []:
            trimestre = row.get("D3N") or trimestre
            local = row.get("D1N") or local
            if row.get("D2C") == "282":
                litros = self._numero(row.get("V"))
                # a fonte entrega em "Mil litros" — normaliza pra litros
                if litros is not None and "mil" in (row.get("MN") or "").lower():
                    litros *= 1000
            elif row.get("D2C") == "2522":
                preco = self._numero(row.get("V"))
        item = Leite(trimestre=trimestre, localidade=local or "Brasil", litros=litros, preco_medio=preco)
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=[item.model_dump(mode="json")], total=1,
            meta={"trimestre": trimestre, "fonte": FONTE_TRIMESTRAIS},
        )

    async def _municipios(self, recurso: str, params: dict) -> NormalizedResponse:
        """PAM municipal (tabela 5457): os municipios que mais produzem uma
        cultura numa UF. Os codigos de produto DIFEREM da 1612 — mapa proprio."""
        self._checa(recurso, params, {"produto", "uf", "limit"})
        produto = str(params.get("produto", "soja")).lower()
        if produto not in PAM_MUNICIPAL:
            raise ParametroInvalido(recurso, [f"produto={produto}"], sorted(PAM_MUNICIPAL))
        sigla = normaliza_uf(params.get("uf", ""))
        cod_uf = UF_IBGE.get(sigla) if sigla else None
        if cod_uf is None:
            raise ParametroInvalido(recurso, ["uf"], sorted(UF_IBGE))
        limit = str(params.get("limit", 15))
        if not limit.isdigit() or not (1 <= int(limit) <= 100):
            raise ParametroInvalido(recurso, ["limit"], ["limit entre 1 e 100"])
        path = f"/values/t/5457/n6/in n3 {cod_uf}/v/214/p/last/c782/{PAM_MUNICIPAL[produto]}"
        bruto = await self.get_json(path)
        registros = self._parse(bruto, None)
        registros = registros[: int(limit)]
        ano = registros[0]["ano"] if registros else None
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=registros, total=len(registros),
            meta={"produto": produto, "uf": sigla, "ano": ano, "fonte": FONTE},
        )

    def _checa(self, recurso: str, params: dict, aceitos: set) -> None:
        invalidos = sorted(set(params) - aceitos)
        if invalidos:
            raise ParametroInvalido(recurso, invalidos, sorted(aceitos))

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
