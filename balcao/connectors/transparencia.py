"""Portal da Transparência (CGU): pra onde vai o dinheiro público federal.
Primeira fonte com chave do Balcão — o token é grátis (cadastro por e-mail)
e vai no header chave-api-dados, lido do .env. Os quirks da fonte ficam
todos aqui: valores em formato brasileiro ("8.000,00"), datas dd/mm/aaaa,
paginação por número fixo e rate limit que muda por horário."""

import asyncio
from typing import Any

from balcao.config import get_settings
from balcao.connectors.base import BaseConnector, NormalizedResponse, register
from balcao.exceptions import ChaveFaltando, ErroUpstream, ParametroInvalido, RecursoNaoEncontrado
from balcao.models import BeneficioSocial, Emenda, Sancao
from balcao.normalize import limpa_texto, para_data, so_digitos, valor_br

FONTE = {
    "nome": "Portal da Transparência — CGU",
    "url": "https://portaldatransparencia.gov.br",
    "nota": (
        "Dados oficiais do governo federal publicados pela Controladoria-Geral da "
        "União. Emendas por autor, sanções (CEIS/CNEP) por CNPJ ou CPF e a folha "
        "do Novo Bolsa Família por município."
    ),
}

PARAMS_EMENDAS = {"ano", "autor", "pagina"}
PARAMS_SANCOES = {"documento", "pagina"}
PARAMS_BOLSA = {"municipio", "mes", "pagina"}


@register
class TransparenciaConnector(BaseConnector):
    name = "transparencia"
    base_url = "https://api.portaldatransparencia.gov.br/api-de-dados"
    requires_key = True
    description = "Portal da Transparência (CGU): emendas parlamentares, sanções por CNPJ/CPF e Bolsa Família"
    resources = {
        "emendas": "emendas parlamentares (params: ano, autor, pagina)",
        "sancoes": "CEIS + CNEP juntos: quem está punido (params: documento = CNPJ ou CPF, pagina)",
        "bolsa-familia": "folha do Novo Bolsa Família num município (params: municipio = código IBGE, mes = AAAAMM)",
    }

    def __init__(self, *args, chave: str | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._chave = chave

    @property
    def chave(self) -> str:
        if self._chave is not None:
            return self._chave
        return get_settings().transparencia_api_key

    async def fetch(self, recurso: str, **params: Any) -> NormalizedResponse:
        if not self.chave:
            raise ChaveFaltando(self.name, "TRANSPARENCIA_API_KEY")
        partes = [p for p in recurso.strip("/").split("/") if p]
        match partes:
            case ["emendas"]:
                return await self._emendas(recurso, params)
            case ["sancoes"]:
                return await self._sancoes(recurso, params)
            case ["bolsa-familia"] | ["bolsa_familia"]:
                return await self._bolsa(recurso, params)
            case _:
                raise RecursoNaoEncontrado(self.name, recurso, sorted(self.resources))

    async def _api(self, path: str, consulta: dict) -> Any:
        return await self.get_json(
            path, params=consulta, timeout=30, headers={"chave-api-dados": self.chave}
        )

    async def _emendas(self, recurso: str, params: dict) -> NormalizedResponse:
        self._valida(recurso, params, PARAMS_EMENDAS)
        pagina = self._pagina(recurso, params)
        consulta: dict = {"pagina": pagina}
        if params.get("ano"):
            consulta["ano"] = self._inteiro(recurso, "ano", params["ano"])
        if params.get("autor"):
            consulta["nomeAutor"] = str(params["autor"])
        bruto = await self._api("/emendas", consulta)

        itens = []
        for e in bruto if isinstance(bruto, list) else []:
            itens.append(
                Emenda(
                    codigo=str(e.get("codigoEmenda") or ""),
                    ano=int(e.get("ano") or 0),
                    tipo=limpa_texto(e.get("tipoEmenda")) or None,
                    autor=limpa_texto(e.get("nomeAutor") or e.get("autor")),
                    localidade=limpa_texto(e.get("localidadeDoGasto")) or None,
                    funcao=limpa_texto(e.get("funcao")) or None,
                    valor_empenhado=valor_br(e.get("valorEmpenhado")),
                    valor_liquidado=valor_br(e.get("valorLiquidado")),
                    valor_pago=valor_br(e.get("valorPago")),
                ).model_dump(mode="json")
            )
        meta = {"pagina": pagina, "tem_proxima": len(itens) >= 15, "fonte": FONTE}
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=itens, total=len(itens), meta=meta
        )

    async def _sancoes(self, recurso: str, params: dict) -> NormalizedResponse:
        self._valida(recurso, params, PARAMS_SANCOES)
        pagina = self._pagina(recurso, params)
        documento = so_digitos(str(params.get("documento", "")))
        if not documento:
            raise ParametroInvalido(recurso, ["documento"], sorted(PARAMS_SANCOES))
        consulta = {"codigoSancionado": documento, "pagina": pagina}

        # os dois cadastros de punidos, em paralelo; um falhar não cala o outro
        ceis, cnep = await asyncio.gather(
            self._api("/ceis", consulta),
            self._api("/cnep", consulta),
            return_exceptions=True,
        )
        erros = []
        itens = []
        for cadastro, bruto in (("CEIS", ceis), ("CNEP", cnep)):
            if isinstance(bruto, ErroUpstream):
                erros.append(cadastro)
                continue
            if isinstance(bruto, BaseException):
                raise bruto
            for s in bruto if isinstance(bruto, list) else []:
                itens.append(self._norm_sancao(cadastro, s).model_dump(mode="json"))

        meta: dict = {"documento": documento, "pagina": pagina, "fonte": FONTE}
        if erros:
            meta["indisponiveis"] = erros
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=itens, total=len(itens), meta=meta
        )

    @staticmethod
    def _norm_sancao(cadastro: str, s: dict) -> Sancao:
        sancionado = s.get("sancionado") or {}
        tipo = s.get("tipoSancao") or {}
        orgao = s.get("orgaoSancionador") or {}
        return Sancao(
            cadastro=cadastro,
            sancionado=limpa_texto(sancionado.get("nome")),
            documento=limpa_texto(sancionado.get("codigoFormatado")) or None,
            tipo=limpa_texto(tipo.get("descricaoResumida")) or None,
            orgao=limpa_texto(orgao.get("nome")) or None,
            uf=limpa_texto(orgao.get("siglaUf")) or None,
            esfera=limpa_texto(orgao.get("esfera")) or None,
            inicio=para_data(s.get("dataInicioSancao")),
            fim=para_data(s.get("dataFimSancao")),
        )

    async def _bolsa(self, recurso: str, params: dict) -> NormalizedResponse:
        self._valida(recurso, params, PARAMS_BOLSA)
        pagina = self._pagina(recurso, params)
        ibge = so_digitos(str(params.get("municipio", "")))
        if not ibge or len(ibge) != 7:
            raise ParametroInvalido(recurso, ["municipio"], ["municipio = código IBGE de 7 dígitos"])
        mes = so_digitos(str(params.get("mes", "")))
        if not mes or len(mes) != 6:
            raise ParametroInvalido(recurso, ["mes"], ["mes = AAAAMM, ex 202605"])
        consulta = {"codigoIbge": ibge, "mesAno": mes, "pagina": pagina}
        bruto = await self._api("/novo-bolsa-familia-por-municipio", consulta)

        itens = []
        for b in bruto if isinstance(bruto, list) else []:
            municipio = b.get("municipio") or {}
            uf = (municipio.get("uf") or {}).get("sigla")
            itens.append(
                BeneficioSocial(
                    programa=limpa_texto((b.get("tipo") or {}).get("descricao")) or "Novo Bolsa Família",
                    municipio=limpa_texto(municipio.get("nomeIBGE")),
                    uf=uf,
                    ibge=int(municipio.get("codigoIBGE") or 0) or None,
                    referencia=para_data(b.get("dataReferencia")),
                    beneficiarios=b.get("quantidadeBeneficiados"),
                    valor=valor_br(b.get("valor")) or 0,
                ).model_dump(mode="json")
            )
        meta = {"municipio": ibge, "mes": mes, "fonte": FONTE}
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=itens, total=len(itens), meta=meta
        )

    def _valida(self, recurso: str, params: dict, aceitos: set) -> None:
        invalidos = sorted(set(params) - aceitos)
        if invalidos:
            raise ParametroInvalido(recurso, invalidos, sorted(aceitos))

    def _pagina(self, recurso: str, params: dict) -> int:
        return max(1, self._inteiro(recurso, "pagina", params.get("pagina", 1)))

    def _inteiro(self, recurso: str, nome: str, valor: Any) -> int:
        if not str(valor).isdigit():
            raise ParametroInvalido(recurso, [nome], [f"{nome} numérico"])
        return int(valor)
