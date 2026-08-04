from typing import Any

from pydantic import ValidationError

from balcao.connectors.base import BaseConnector, NormalizedResponse, register
from balcao.exceptions import ParametroInvalido, RecursoNaoEncontrado
from balcao.models import Estado, FrequenciaNome, Municipio, NomeNoEstado, RankingNome
from balcao.normalize import limpa_texto, normaliza_uf

# a API de nomes vive na v2 (a base do conector é v1)
NOMES_URL = "https://servicodados.ibge.gov.br/api/v2/censos/nomes"

UF_POR_CODIGO = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP", "17": "TO",
    "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB", "26": "PE", "27": "AL",
    "28": "SE", "29": "BA", "31": "MG", "32": "ES", "33": "RJ", "35": "SP",
    "41": "PR", "42": "SC", "43": "RS", "50": "MS", "51": "MT", "52": "GO", "53": "DF",
}

FONTE_NOMES = {
    "nome": "IBGE, Nomes do Censo 2010",
    "url": "https://censo2010.ibge.gov.br/nomes/",
    "nota": (
        "Frequência de primeiros nomes apurada no Censo 2010, o retrato é "
        "congelado ali: nome que virou moda depois de 2010 não aparece. A fonte "
        "devolve tudo em caixa alta e sem acento."
    ),
}


@register
class IbgeConnector(BaseConnector):
    name = "ibge"
    base_url = "https://servicodados.ibge.gov.br/api/v1"
    description = "IBGE: estados e municípios do Brasil"
    suporta_busca = True
    resources = {
        "estados": "as 27 unidades da federação; sem filtros",
        "municipios": "municípios do país; filtros: uf (sem ele vêm os 5570)",
        "nomes": (
            "seu nome no Brasil, do Censo 2010 (params: nome obrigatório; sexo = m|f; "
            "por = decada|uf)"
        ),
        "nomes/ranking": "os nomes mais comuns do Brasil (params: decada, sexo = m|f, limit)",
    }

    async def fetch(self, recurso: str, **params: Any) -> NormalizedResponse:
        partes = [p for p in recurso.strip("/").split("/") if p]
        match partes:
            case ["estados"]:
                return await self._estados(recurso, params)
            case ["municipios"]:
                return await self._municipios(recurso, params)
            case ["nomes", "ranking"]:
                return await self._nomes_ranking(recurso, params)
            case ["nomes"]:
                return await self._nomes(recurso, params)
            case _:
                raise RecursoNaoEncontrado(self.name, recurso, sorted(self.resources))

    async def buscar(self, q: str) -> list[dict]:
        termo = q.casefold()
        estados = await self._estados("estados", {})
        achados = [
            {"tipo_resultado": "estado", **e}
            for e in estados.dados
            if termo in e["nome"].casefold() or termo == e["sigla"].casefold()
        ]
        municipios = await self._municipios("municipios", {})
        achados += [
            {"tipo_resultado": "municipio", **m}
            for m in municipios.dados
            if termo in m["nome"].casefold()
        ][:10]
        return achados

    async def _estados(self, recurso: str, params: dict) -> NormalizedResponse:
        if params:
            raise ParametroInvalido(recurso, sorted(params), [])
        bruto = await self.get_json("/localidades/estados", params={"orderBy": "nome"})
        itens, descartados = self._normaliza_lote(bruto, self._norm_estado)
        return self._envelopa(recurso, itens, descartados)

    async def _municipios(self, recurso: str, params: dict) -> NormalizedResponse:
        invalidos = sorted(set(params) - {"uf"})
        if invalidos:
            raise ParametroInvalido(recurso, invalidos, ["uf"])
        uf = normaliza_uf(params.get("uf"))
        if params.get("uf") and uf is None:
            raise ParametroInvalido(recurso, ["uf"], ["uf"])

        path = f"/localidades/estados/{uf}/municipios" if uf else "/localidades/municipios"
        bruto = await self.get_json(path, params={"orderBy": "nome"})
        itens, descartados = self._normaliza_lote(bruto, self._norm_municipio)
        return self._envelopa(recurso, itens, descartados)

    def _normaliza_lote(self, bruto: list, normalizador) -> tuple[list, int]:
        itens = []
        descartados = 0
        for b in bruto or []:
            try:
                itens.append(normalizador(b).model_dump(mode="json"))
            except (ValidationError, KeyError):
                descartados += 1
        return itens, descartados

    def _envelopa(self, recurso: str, itens: list, descartados: int) -> NormalizedResponse:
        meta = {"descartados": descartados} if descartados else {}
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=itens, total=len(itens), meta=meta
        )

    def _norm_estado(self, b: dict) -> Estado:
        return Estado(
            id=b["id"],
            sigla=b["sigla"],
            nome=b["nome"],
            regiao=(b.get("regiao") or {}).get("nome"),
        )

    def _norm_municipio(self, b: dict) -> Municipio:
        # a UF do municipio vem enterrada em tres niveis de aninhamento, e o
        # caminho muda conforme a divisao territorial usada na resposta
        uf_info = (((b.get("microrregiao") or {}).get("mesorregiao") or {}).get("UF") or {})
        if not uf_info:
            uf_info = (
                ((b.get("regiao-imediata") or {}).get("regiao-intermediaria") or {}).get("UF")
                or {}
            )
        return Municipio(
            id=b["id"],
            nome=b["nome"],
            uf=uf_info.get("sigla"),
            regiao=(uf_info.get("regiao") or {}).get("nome"),
        )

    def _sexo(self, recurso: str, params: dict) -> str | None:
        sexo = str(params.get("sexo", "")).strip().upper()
        if sexo and sexo not in {"M", "F"}:
            raise ParametroInvalido(recurso, ["sexo"], ["m", "f"])
        return sexo or None

    @staticmethod
    def _decada(periodo: str) -> str:
        # a fonte fala "[1990,2000[" e "1930[", o leitor entende "1990" e "até 1930"
        p = (periodo or "").strip("[]")
        if "," in p:
            return p.split(",")[0]
        return f"até {p}" if p else "?"

    async def _nomes(self, recurso: str, params: dict) -> NormalizedResponse:
        invalidos = sorted(set(params) - {"nome", "sexo", "por"})
        if invalidos:
            raise ParametroInvalido(recurso, invalidos, ["nome", "sexo", "por"])
        nome = limpa_texto(str(params.get("nome", ""))).strip()
        if not nome or not nome.replace(" ", "").isalpha():
            raise ParametroInvalido(recurso, ["nome"], ["um primeiro nome (só letras)"])
        por = str(params.get("por", "decada")).lower()
        if por not in {"decada", "uf"}:
            raise ParametroInvalido(recurso, ["por"], ["decada", "uf"])
        consulta: dict = {}
        if sexo := self._sexo(recurso, params):
            consulta["sexo"] = sexo
        if por == "uf":
            consulta["groupBy"] = "UF"

        bruto = await self.get_json(f"{NOMES_URL}/{nome.split()[0]}", params=consulta)
        entradas = bruto if isinstance(bruto, list) else []
        itens: list[dict] = []
        if por == "decada":
            for r in entradas[0].get("res", []) if entradas else []:
                itens.append(
                    FrequenciaNome(
                        nome=entradas[0].get("nome") or nome.upper(),
                        decada=self._decada(r.get("periodo")),
                        frequencia=int(r.get("frequencia") or 0),
                    ).model_dump(mode="json")
                )
        else:
            for e in entradas:
                uf = UF_POR_CODIGO.get(str(e.get("localidade")))
                r = (e.get("res") or [{}])[0]
                if not uf:
                    continue
                itens.append(
                    NomeNoEstado(
                        nome=nome.upper(),
                        uf=uf,
                        frequencia=int(r.get("frequencia") or 0),
                        por_100k=float(r["proporcao"]) if r.get("proporcao") is not None else None,
                    ).model_dump(mode="json")
                )
            itens.sort(key=lambda i: i["por_100k"] or 0, reverse=True)

        meta = {"nome": nome.upper(), "por": por, "total_pessoas": sum(i["frequencia"] for i in itens) if por == "decada" else None, "fonte": FONTE_NOMES}
        if not itens:
            meta["aviso"] = "o Censo 2010 não registrou esse nome (menos de 10 ocorrências)"
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=itens, total=len(itens), meta=meta
        )

    async def _nomes_ranking(self, recurso: str, params: dict) -> NormalizedResponse:
        invalidos = sorted(set(params) - {"decada", "sexo", "limit"})
        if invalidos:
            raise ParametroInvalido(recurso, invalidos, ["decada", "sexo", "limit"])
        limit = str(params.get("limit", 20))
        if not limit.isdigit() or not (1 <= int(limit) <= 20):
            raise ParametroInvalido(recurso, ["limit"], ["1..20 (a fonte só devolve 20)"])
        consulta: dict = {}
        decada = str(params.get("decada", "")).strip()
        if decada:
            if not decada.isdigit() or not (1930 <= int(decada) <= 2000) or int(decada) % 10:
                raise ParametroInvalido(recurso, ["decada"], ["1930, 1940 … 2000"])
            consulta["decada"] = decada
        if sexo := self._sexo(recurso, params):
            consulta["sexo"] = sexo

        bruto = await self.get_json(f"{NOMES_URL}/ranking", params=consulta)
        entradas = bruto if isinstance(bruto, list) else []
        itens = [
            RankingNome(
                posicao=int(r.get("ranking") or 0),
                nome=limpa_texto(r.get("nome")) or "?",
                frequencia=int(r.get("frequencia") or 0),
            ).model_dump(mode="json")
            for r in (entradas[0].get("res", []) if entradas else [])
        ][: int(limit)]
        meta = {"decada": decada or "todas", "sexo": consulta.get("sexo", "todos"), "fonte": FONTE_NOMES}
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=itens, total=len(itens), meta=meta
        )
