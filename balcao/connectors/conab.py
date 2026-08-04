"""CONAB: a safra em curso e o preço pago ao produtor, dos arquivos TXT que
a companhia publica diariamente (~11h UTC). Não há API; são CSVs com ';',
Latin-1 e campos com padding de espaço; cada arquivo tem seu proprio dialeto
de decimal (ponto no levantamento, vírgula nos preços). O parse mora aqui e
o cache do gateway poupa os ~6 MB por consulta."""

from typing import Any

from balcao.connectors.base import BaseConnector, NormalizedResponse, register
from balcao.exceptions import ErroUpstream, ParametroInvalido, RecursoNaoEncontrado
from balcao.models import PrecoAgro, SafraConab
from balcao.normalize import normaliza_uf

FONTE = {
    "nome": "CONAB, Companhia Nacional de Abastecimento",
    "url": "https://portaldeinformacoes.conab.gov.br",
    "nota": (
        "Os levantamentos oficiais de safra (12 por ano agrícola) e os preços "
        "agropecuários apurados pela CONAB, atualizados diariamente."
    ),
}


def _num_ponto(s: str) -> float | None:
    s = s.strip()
    try:
        return float(s)
    except ValueError:
        return None


def _num_virgula(s: str) -> float | None:
    s = s.strip().replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


@register
class ConabConnector(BaseConnector):
    name = "conab"
    base_url = "https://portaldeinformacoes.conab.gov.br/downloads/arquivos"
    description = "CONAB: levantamento mensal da safra de grãos e preços agropecuários por UF"
    resources = {
        "safra": "o levantamento mais recente da safra em curso (params: produto, uf; sem uf soma o Brasil)",
        "precos": "preço médio mensal por kg e UF (params: produto, uf)",
    }

    async def fetch(self, recurso: str, **params: Any) -> NormalizedResponse:
        partes = [p for p in recurso.strip("/").split("/") if p]
        match partes:
            case ["safra"]:
                return await self._safra(recurso, params)
            case ["precos"]:
                return await self._precos(recurso, params)
            case _:
                raise RecursoNaoEncontrado(self.name, recurso, sorted(self.resources))

    async def _txt(self, arquivo: str) -> list[list[str]]:
        resp = await self._request("GET", f"/{arquivo}", timeout=90)
        texto = resp.content.decode("latin-1")
        linhas = [l for l in texto.splitlines() if l.strip()]
        if len(linhas) < 2:
            raise ErroUpstream(self.name)
        return [[campo.strip() for campo in l.split(";")] for l in linhas[1:]]

    def _valida(self, recurso: str, params: dict, aceitos: set) -> None:
        invalidos = sorted(set(params) - aceitos)
        if invalidos:
            raise ParametroInvalido(recurso, invalidos, sorted(aceitos))

    async def _safra(self, recurso: str, params: dict) -> NormalizedResponse:
        self._valida(recurso, params, {"produto", "uf"})
        produto_filtro = str(params.get("produto", "")).strip().upper()
        uf = normaliza_uf(params["uf"]) if params.get("uf") else None
        if params.get("uf") and uf is None:
            raise ParametroInvalido(recurso, ["uf"], ["sigla de UF"])

        linhas = await self._txt("LevantamentoGraos.txt")
        # colunas: ano_agricola;safra;uf;produto;id_produto;id_levantamento;
        # dsc_levantamento;area_plantada;producao;produtividade
        ano_corrente = max((l[0] for l in linhas if len(l) >= 10), default="")
        do_ano = [l for l in linhas if len(l) >= 10 and l[0] == ano_corrente]
        ultimo_lev = max((l[5] for l in do_ano), default="")
        do_lev = [l for l in do_ano if l[5] == ultimo_lev]

        # soma as safras (1ª/2ª/única) por produto, e por UF quando pedida
        acum: dict[str, dict] = {}
        rotulo_lev = do_lev[0][6] if do_lev else ""
        for l in do_lev:
            if uf and l[2].upper() != uf:
                continue
            if produto_filtro and produto_filtro not in l[3].upper():
                continue
            reg = acum.setdefault(l[3].title(), {"area": 0.0, "prod": 0.0})
            reg["area"] += _num_ponto(l[7]) or 0.0
            reg["prod"] += _num_ponto(l[8]) or 0.0
        itens = [
            SafraConab(
                ano_agricola=ano_corrente,
                levantamento=rotulo_lev,
                produto=nome,
                uf=uf,
                area_mil_ha=round(v["area"], 1) or None,
                producao_mil_t=round(v["prod"], 1) or None,
                produtividade=round(v["prod"] / v["area"], 2) if v["area"] else None,
            ).model_dump(mode="json")
            for nome, v in acum.items()
        ]
        itens.sort(key=lambda x: x["producao_mil_t"] or 0, reverse=True)
        meta = {
            "ano_agricola": ano_corrente,
            "levantamento": rotulo_lev,
            "fonte": FONTE,
        }
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=itens, total=len(itens), meta=meta
        )

    async def _precos(self, recurso: str, params: dict) -> NormalizedResponse:
        self._valida(recurso, params, {"produto", "uf"})
        produto_filtro = str(params.get("produto", "soja")).strip().upper()
        uf = normaliza_uf(params["uf"]) if params.get("uf") else None
        if params.get("uf") and uf is None:
            raise ParametroInvalido(recurso, ["uf"], ["sigla de UF"])

        linhas = await self._txt("PrecosMensalUF.txt")
        # colunas: produto;classificacao;id_produto;uf;regiao;ano;mes;nivel;valor_kg
        # o preço mais novo de cada UF pro produto pedido, no nível produtor
        melhores: dict[str, list[str]] = {}
        for l in linhas:
            if len(l) < 9:
                continue
            if produto_filtro not in l[0].upper():
                continue
            if "PRODUTOR" not in l[7].upper():
                continue
            if uf and l[3].upper() != uf:
                continue
            chave = l[3]
            atual = melhores.get(chave)
            if atual is None or (l[5], l[6].zfill(2)) > (atual[5], atual[6].zfill(2)):
                melhores[chave] = l
        itens = [
            PrecoAgro(
                produto=l[0].title(),
                uf=l[3],
                nivel=l[7].title() or None,
                periodo=f"{l[5]}-{l[6].zfill(2)}",
                valor_kg=_num_virgula(l[8]),
            ).model_dump(mode="json")
            for l in melhores.values()
        ]
        itens.sort(key=lambda x: x["valor_kg"] or 0, reverse=True)
        meta = {"produto": produto_filtro.title(), "fonte": FONTE}
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=itens, total=len(itens), meta=meta
        )
