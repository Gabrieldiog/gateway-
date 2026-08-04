from typing import Any

from pydantic import ValidationError

from balcao.connectors.base import BaseConnector, NormalizedResponse, register
from balcao.exceptions import ParametroInvalido, RecursoNaoEncontrado
from balcao.models import Estabelecimento
from balcao.normalize import limpa_texto, normaliza_uf, so_digitos

# código IBGE de 2 dígitos de cada UF (o CNES usa esse número em codigo_uf)
UF_IBGE = {
    "RO": 11, "AC": 12, "AM": 13, "RR": 14, "PA": 15, "AP": 16, "TO": 17,
    "MA": 21, "PI": 22, "CE": 23, "RN": 24, "PB": 25, "PE": 26, "AL": 27,
    "SE": 28, "BA": 29, "MG": 31, "ES": 32, "RJ": 33, "SP": 35, "PR": 41,
    "SC": 42, "RS": 43, "MS": 50, "MT": 51, "GO": 52, "DF": 53,
}
IBGE_UF = {v: k for k, v in UF_IBGE.items()}

# tabela de tipos do CNES (estável); o estabelecimento só traz o código
TIPO_UNIDADE = {
    1: "POSTO DE SAUDE",
    2: "CENTRO DE SAUDE/UNIDADE BASICA",
    4: "POLICLINICA",
    5: "HOSPITAL GERAL",
    7: "HOSPITAL ESPECIALIZADO",
    15: "UNIDADE MISTA",
    20: "PRONTO SOCORRO GERAL",
    21: "PRONTO SOCORRO ESPECIALIZADO",
    22: "CONSULTORIO ISOLADO",
    32: "UNIDADE MOVEL FLUVIAL",
    36: "CLINICA/CENTRO DE ESPECIALIDADE",
    39: "UNIDADE DE APOIO DIAGNOSE E TERAPIA (SADT ISOLADO)",
    40: "UNIDADE MOVEL TERRESTRE",
    42: "UNIDADE MOVEL DE NIVEL PRE-HOSPITALAR NA AREA DE URGENCIA",
    43: "FARMACIA",
    50: "UNIDADE DE VIGILANCIA EM SAUDE",
    60: "COOPERATIVA OU EMPRESA DE CESSAO DE TRABALHADORES NA SAUDE",
    61: "CENTRO DE PARTO NORMAL - ISOLADO",
    62: "HOSPITAL/DIA - ISOLADO",
    64: "CENTRAL DE REGULACAO DE SERVICOS DE SAUDE",
    67: "LABORATORIO CENTRAL DE SAUDE PUBLICA LACEN",
    68: "CENTRAL DE GESTAO EM SAUDE",
    69: "CENTRO DE ATENCAO HEMOTERAPIA E OU HEMATOLOGICA",
    70: "CENTRO DE ATENCAO PSICOSSOCIAL",
    71: "CENTRO DE APOIO A SAUDE DA FAMILIA",
    72: "UNIDADE DE ATENCAO A SAUDE INDIGENA",
    73: "PRONTO ATENDIMENTO",
    74: "POLO ACADEMIA DA SAUDE",
    75: "TELESSAUDE",
    76: "CENTRAL DE REGULACAO MEDICA DAS URGENCIAS",
    77: "SERVICO DE ATENCAO DOMICILIAR ISOLADO(HOME CARE)",
    78: "UNIDADE DE ATENCAO EM REGIME RESIDENCIAL",
    79: "OFICINA ORTOPEDICA",
    80: "LABORATORIO DE SAUDE PUBLICA",
    81: "CENTRAL DE REGULACAO DO ACESSO",
    82: "CENTRAL DE NOTIFICACAO,CAPTACAO E DISTRIB DE ORGAOS ESTADUAL",
    83: "POLO DE PREVENCAO DE DOENCAS E AGRAVOS E PROMOCAO DA SAUDE",
}

# nomes nossos -> o que o CNES espera na query
FILTROS = {"uf", "municipio", "tipo", "limite", "pagina"}
LIMITE_PADRAO = 20
LIMITE_MAX = 100


@register
class SusConnector(BaseConnector):
    name = "sus"
    base_url = "https://apidadosabertos.saude.gov.br"
    description = "Ministério da Saúde (CNES): estabelecimentos de saúde, hospitais, UBS, prontos-socorros"
    resources = {
        "estabelecimentos": f"estabelecimentos de saúde; filtros: {', '.join(sorted(FILTROS))}",
        "estabelecimentos/{cnes}": "detalhe de um estabelecimento pelo código CNES",
    }

    async def fetch(self, recurso: str, **params: Any) -> NormalizedResponse:
        partes = [p for p in recurso.strip("/").split("/") if p]
        match partes:
            case ["estabelecimentos"]:
                return await self._estabelecimentos(recurso, params)
            case ["estabelecimentos", cnes] if cnes.isdigit():
                return await self._detalhe(recurso, cnes)
            case _:
                raise RecursoNaoEncontrado(self.name, recurso, sorted(self.resources))

    async def _estabelecimentos(self, recurso: str, params: dict) -> NormalizedResponse:
        invalidos = sorted(set(params) - FILTROS)
        if invalidos:
            raise ParametroInvalido(recurso, invalidos, sorted(FILTROS))

        limite, offset, pagina = self._paginacao(recurso, params)
        query: dict[str, Any] = {"limit": limite, "offset": offset}
        if "uf" in params:
            query["codigo_uf"] = self._codigo_uf(recurso, params["uf"])
        if "municipio" in params:
            query["codigo_municipio"] = self._inteiro(recurso, "municipio", params["municipio"])
        if "tipo" in params:
            query["codigo_tipo_unidade"] = self._inteiro(recurso, "tipo", params["tipo"])

        bruto = await self.get_json("/cnes/estabelecimentos", params=query)
        crus = bruto.get("estabelecimentos", []) if isinstance(bruto, dict) else []
        itens, descartados = [], 0
        for b in crus:
            try:
                itens.append(self._norm(b).model_dump(mode="json"))
            except (ValidationError, KeyError):
                descartados += 1
        # o CNES não devolve total nem link de próxima; se veio página cheia, presume que há mais
        meta: dict[str, Any] = {"pagina": pagina, "limite": limite, "tem_proxima": len(crus) >= limite}
        if descartados:
            meta["descartados"] = descartados
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=itens, total=len(itens), meta=meta
        )

    async def _detalhe(self, recurso: str, cnes: str) -> NormalizedResponse:
        bruto = await self.get_json(f"/cnes/estabelecimentos/{cnes}")
        if not isinstance(bruto, dict) or not bruto.get("codigo_cnes"):
            raise RecursoNaoEncontrado(self.name, recurso, sorted(self.resources))
        return NormalizedResponse(
            fonte=self.name,
            recurso=recurso,
            dados=[self._norm(bruto).model_dump(mode="json")],
            total=1,
        )

    def _paginacao(self, recurso: str, params: dict) -> tuple[int, int, int]:
        limite = self._inteiro(recurso, "limite", params.get("limite"), LIMITE_PADRAO)
        limite = max(1, min(limite, LIMITE_MAX))
        pagina = max(1, self._inteiro(recurso, "pagina", params.get("pagina"), 1))
        return limite, (pagina - 1) * limite, pagina

    def _inteiro(self, recurso: str, nome: str, valor: Any, padrao: int | None = None) -> int:
        if valor is None:
            return padrao if padrao is not None else 0
        texto = str(valor)
        if not texto.isdigit():
            raise ParametroInvalido(recurso, [f"{nome}={valor}"], [f"{nome} numérico"])
        return int(texto)

    def _codigo_uf(self, recurso: str, valor: str) -> int:
        sigla = normaliza_uf(valor)
        cod = UF_IBGE.get(sigla) if sigla else None
        if cod is None:
            raise ParametroInvalido(recurso, [f"uf={valor}"], sorted(UF_IBGE))
        return cod

    def _norm(self, b: dict) -> Estabelecimento:
        cod_uf = b.get("codigo_uf")
        tipo_cod = b.get("codigo_tipo_unidade")
        numero = str(b.get("numero_estabelecimento") or "").strip()
        rua = limpa_texto(b.get("endereco_estabelecimento"))
        endereco = ", ".join(p for p in [rua, numero] if p) or None
        email = (b.get("endereco_email_estabelecimento") or "").strip().lower() or None
        return Estabelecimento(
            cnes=b["codigo_cnes"],
            nome=limpa_texto(b.get("nome_fantasia") or b.get("nome_razao_social")),
            tipo=TIPO_UNIDADE.get(tipo_cod),
            tipo_codigo=tipo_cod,
            esfera=limpa_texto(b.get("descricao_esfera_administrativa")) or None,
            cnpj=so_digitos(b.get("numero_cnpj") or b.get("numero_cnpj_entidade")),
            municipio_id=b.get("codigo_municipio"),
            uf=IBGE_UF.get(cod_uf),
            bairro=limpa_texto(b.get("bairro_estabelecimento")) or None,
            endereco=endereco,
            telefone=limpa_texto(b.get("numero_telefone_estabelecimento")) or None,
            email=email,
            latitude=b.get("latitude_estabelecimento_decimo_grau"),
            longitude=b.get("longitude_estabelecimento_decimo_grau"),
        )
