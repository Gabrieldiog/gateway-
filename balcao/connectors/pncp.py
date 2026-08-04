"""PNCP (Portal Nacional de Contratações Públicas): o que o governo, todas
as esferas; está comprando. API de consulta aberta, sem chave, mas cheia de
manha: datas em AAAAMMDD sem separador, modalidade obrigatória por código de
enum que só vive num manual em PDF, tamanhoPagina com mínimo de 10 e um
envelope de erro próprio. O conector esconde tudo isso."""

import json
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from balcao.connectors.base import BaseConnector, NormalizedResponse, register
from balcao.exceptions import ParametroInvalido, RecursoNaoEncontrado
from balcao.models import ArquivoCompra, ContratoPublico, ItemCompra, Licitacao, VencedorItem
from balcao.normalize import limpa_texto, para_data, so_digitos

# enum de modalidades da Lei 14.133 (manual do PNCP); o cliente usa o slug
MODALIDADES = {
    "leilao-eletronico": 1,
    "dialogo-competitivo": 2,
    "concurso": 3,
    "concorrencia-eletronica": 4,
    "concorrencia-presencial": 5,
    "pregao-eletronico": 6,
    "pregao-presencial": 7,
    "dispensa": 8,
    "inexigibilidade": 9,
    "manifestacao-de-interesse": 10,
    "pre-qualificacao": 11,
    "credenciamento": 12,
    "leilao-presencial": 13,
}

ESFERAS = {"F": "federal", "E": "estadual", "M": "municipal", "D": "distrital"}

PARAMS_LICITACOES = {"de", "ate", "modalidade", "uf", "municipio", "pagina"}
PARAMS_CONTRATOS = {"de", "ate", "cnpj", "pagina"}

FONTE = {
    "nome": "PNCP, Portal Nacional de Contratações Públicas",
    "url": "https://pncp.gov.br",
    "nota": (
        "Licitações e contratos que União, estados e municípios são obrigados a "
        "publicar pela Lei 14.133. Valores estimados podem mudar na homologação."
    ),
}


@register
class PncpConnector(BaseConnector):
    name = "pncp"
    base_url = "https://pncp.gov.br/api/consulta"
    description = "PNCP: licitações e contratos públicos de todas as esferas (Lei 14.133)"
    resources = {
        "licitacoes": (
            "contratações publicadas no período (params: de, ate = AAAA-MM-DD, "
            f"modalidade = {', '.join(sorted(MODALIDADES))}, uf, municipio, pagina)"
        ),
        "contratos": "contratos assinados no período (params: de, ate, cnpj do órgão, pagina)",
        "itens": "o que está sendo comprado numa contratação, item a item (params: controle = numeroControlePNCP)",
        "resultado": "quem venceu um item: fornecedor, porte, valor homologado (params: controle, item)",
        "arquivos": "os documentos da compra, edital e anexos em PDF (params: controle)",
    }

    async def fetch(self, recurso: str, **params: Any) -> NormalizedResponse:
        partes = [p for p in recurso.strip("/").split("/") if p]
        match partes:
            case ["licitacoes"] | ["contratacoes"]:
                return await self._licitacoes(recurso, params)
            case ["contratos"]:
                return await self._contratos(recurso, params)
            case ["itens"]:
                return await self._itens(recurso, params)
            case ["arquivos"]:
                return await self._arquivos(recurso, params)
            case ["resultado"]:
                return await self._resultado(recurso, params)
            case _:
                raise RecursoNaoEncontrado(self.name, recurso, sorted(self.resources))

    @staticmethod
    def _parse_controle(recurso: str, controle: str) -> tuple[str, int, int]:
        """numeroControlePNCP: '76205699000198-1-000072/2026' → (cnpj, ano, seq)."""
        try:
            resto, ano = controle.strip().split("/")
            cnpj, _, seq = resto.split("-")
            if len(cnpj) != 14 or not cnpj.isdigit():
                raise ValueError
            return cnpj, int(ano), int(seq)
        except (ValueError, AttributeError):
            raise ParametroInvalido(
                recurso, ["controle"], ["controle = numeroControlePNCP (ex 76205699000198-1-000072/2026)"]
            ) from None

    async def _itens(self, recurso: str, params: dict) -> NormalizedResponse:
        """O que exatamente está sendo comprado numa contratação, item a item.
        Vive no lado operacional (/api/pncp), irmão da API de consulta."""
        self._valida(recurso, params, {"controle", "pagina"})
        controle = str(params.get("controle", ""))
        cnpj, ano, seq = self._parse_controle(recurso, controle)
        pagina = self._pagina(recurso, params)
        bruto = await self.get_json(
            f"https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj}/compras/{ano}/{seq}/itens",
            params={"pagina": pagina, "tamanhoPagina": 50},
        )
        itens = []
        for i in bruto if isinstance(bruto, list) else []:
            itens.append(
                ItemCompra(
                    numero=int(i.get("numeroItem") or 0),
                    descricao=limpa_texto(i.get("descricao")) or "sem dado",
                    quantidade=float(i["quantidade"]) if i.get("quantidade") is not None else None,
                    unidade=limpa_texto(i.get("unidadeMedida")) or None,
                    valor_unitario=_decimal(i.get("valorUnitarioEstimado")),
                    valor_total=_decimal(i.get("valorTotal")),
                    situacao=limpa_texto(i.get("situacaoCompraItemNome")) or None,
                    tem_resultado=bool(i.get("temResultado")),
                    beneficio=limpa_texto(i.get("tipoBeneficioNome")) or None,
                ).model_dump(mode="json")
            )
        meta = {"controle": controle, "pagina": pagina, "fonte": FONTE}
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=itens, total=len(itens), meta=meta
        )

    async def _arquivos(self, recurso: str, params: dict) -> NormalizedResponse:
        """Os documentos publicados junto da compra, o edital em PDF é a
        leitura completa que a listagem não dá."""
        self._valida(recurso, params, {"controle"})
        controle = str(params.get("controle", ""))
        cnpj, ano, seq = self._parse_controle(recurso, controle)
        bruto = await self.get_json(
            f"https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj}/compras/{ano}/{seq}/arquivos",
            params={"pagina": 1, "tamanhoPagina": 20},
        )
        itens = []
        for a in bruto if isinstance(bruto, list) else []:
            url = a.get("url") or a.get("uri")
            if not url or a.get("statusAtivo") is False:
                continue
            # o campo titulo costuma ser um codigo; o nome legivel esta no tipo
            tipo = limpa_texto(a.get("tipoDocumentoNome"))
            itens.append(
                ArquivoCompra(
                    titulo=tipo or limpa_texto(a.get("titulo")) or "documento",
                    url=url,
                ).model_dump(mode="json")
            )
        meta = {"controle": controle, "fonte": FONTE}
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=itens, total=len(itens), meta=meta
        )

    async def _resultado(self, recurso: str, params: dict) -> NormalizedResponse:
        """Quem venceu um item: fornecedor, porte e valor homologado.
        Quirk da fonte: item sem resultado responde 204 com corpo vazio."""
        self._valida(recurso, params, {"controle", "item"})
        controle = str(params.get("controle", ""))
        cnpj, ano, seq = self._parse_controle(recurso, controle)
        item = str(params.get("item", ""))
        if not item.isdigit():
            raise ParametroInvalido(recurso, ["item"], ["item = número do item (inteiro)"])
        corpo = await self.get_text(
            f"https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj}/compras/{ano}/{seq}/itens/{item}/resultados",
        )
        bruto = json.loads(corpo) if corpo and corpo.strip() else []
        if isinstance(bruto, dict):
            bruto = [bruto]
        itens = []
        for r in bruto:
            itens.append(
                VencedorItem(
                    item=int(item),
                    fornecedor=limpa_texto(r.get("nomeRazaoSocialFornecedor")) or "sem dado",
                    documento=so_digitos(r.get("niFornecedor")),
                    porte=limpa_texto(r.get("porteFornecedorNome")) or None,
                    valor_unitario=_decimal(r.get("valorUnitarioHomologado")),
                    valor_total=_decimal(r.get("valorTotalHomologado")),
                    quantidade=float(r["quantidadeHomologada"]) if r.get("quantidadeHomologada") is not None else None,
                    desconto_pct=float(r["percentualDesconto"]) if r.get("percentualDesconto") is not None else None,
                    situacao=limpa_texto(r.get("situacaoCompraItemResultadoNome")) or None,
                    data=para_data(r.get("dataResultado")),
                ).model_dump(mode="json")
            )
        meta: dict[str, Any] = {"controle": controle, "item": int(item), "fonte": FONTE}
        if not itens:
            meta["aviso"] = "item ainda sem resultado homologado"
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=itens, total=len(itens), meta=meta
        )

    async def _licitacoes(self, recurso: str, params: dict) -> NormalizedResponse:
        self._valida(recurso, params, PARAMS_LICITACOES)
        de, ate = self._periodo(recurso, params)
        modalidade = self._modalidade(recurso, params.get("modalidade"))
        pagina = self._pagina(recurso, params)
        consulta: dict = {
            "dataInicial": de,
            "dataFinal": ate,
            "codigoModalidadeContratacao": modalidade,
            "pagina": pagina,
        }
        if params.get("uf"):
            consulta["uf"] = str(params["uf"]).upper()
        if params.get("municipio"):
            consulta["codigoMunicipioIbge"] = so_digitos(str(params["municipio"]))
        bruto = await self.get_json("/v1/contratacoes/publicacao", params=consulta)

        itens = []
        for c in bruto.get("data", []) if isinstance(bruto, dict) else []:
            orgao = c.get("orgaoEntidade") or {}
            unidade = c.get("unidadeOrgao") or {}
            itens.append(
                Licitacao(
                    numero_controle=str(c.get("numeroControlePNCP") or ""),
                    ano=int(c.get("anoCompra") or 0),
                    orgao=limpa_texto(orgao.get("razaoSocial")),
                    cnpj_orgao=so_digitos(orgao.get("cnpj")),
                    esfera=ESFERAS.get(orgao.get("esferaId")),
                    municipio=limpa_texto(unidade.get("municipioNome")) or None,
                    uf=limpa_texto(unidade.get("ufSigla")) or None,
                    modalidade=limpa_texto(c.get("modalidadeNome")) or None,
                    objeto=limpa_texto(c.get("objetoCompra")),
                    valor_estimado=_decimal(c.get("valorTotalEstimado")),
                    situacao=limpa_texto(c.get("situacaoCompraNome")) or None,
                    publicada_em=para_data(c.get("dataPublicacaoPncp")),
                    propostas_ate=para_data(c.get("dataEncerramentoProposta")),
                ).model_dump(mode="json")
            )
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=itens, total=len(itens),
            meta=self._meta(bruto, pagina, de=de, ate=ate),
        )

    async def _contratos(self, recurso: str, params: dict) -> NormalizedResponse:
        self._valida(recurso, params, PARAMS_CONTRATOS)
        de, ate = self._periodo(recurso, params)
        pagina = self._pagina(recurso, params)
        consulta: dict = {"dataInicial": de, "dataFinal": ate, "pagina": pagina}
        if params.get("cnpj"):
            consulta["cnpjOrgao"] = so_digitos(str(params["cnpj"]))
        bruto = await self.get_json("/v1/contratos", params=consulta)

        itens = []
        for c in bruto.get("data", []) if isinstance(bruto, dict) else []:
            orgao = c.get("orgaoEntidade") or {}
            unidade = c.get("unidadeOrgao") or {}
            itens.append(
                ContratoPublico(
                    numero_controle=str(c.get("numeroControlePNCP") or ""),
                    ano=int(c.get("anoContrato") or 0),
                    orgao=limpa_texto(orgao.get("razaoSocial")),
                    municipio=limpa_texto(unidade.get("municipioNome")) or None,
                    uf=limpa_texto(unidade.get("ufSigla")) or None,
                    fornecedor=limpa_texto(c.get("nomeRazaoSocialFornecedor")),
                    fornecedor_doc=so_digitos(c.get("niFornecedor")),
                    objeto=limpa_texto(c.get("objetoContrato")),
                    valor=_decimal(c.get("valorGlobal")),
                    assinado_em=para_data(c.get("dataAssinatura")),
                    vigencia_inicio=para_data(c.get("dataVigenciaInicio")),
                    vigencia_fim=para_data(c.get("dataVigenciaFim")),
                ).model_dump(mode="json")
            )
        return NormalizedResponse(
            fonte=self.name, recurso=recurso, dados=itens, total=len(itens),
            meta=self._meta(bruto, pagina, de=de, ate=ate),
        )

    @staticmethod
    def _meta(bruto: Any, pagina: int, de: str, ate: str) -> dict:
        total = bruto.get("totalRegistros") if isinstance(bruto, dict) else None
        paginas = bruto.get("totalPaginas") if isinstance(bruto, dict) else None
        return {
            "periodo": f"{de}-{ate}",
            "pagina": pagina,
            "total_registros": total,
            "tem_proxima": paginas is not None and pagina < paginas,
            "fonte": FONTE,
        }

    def _periodo(self, recurso: str, params: dict) -> tuple[str, str]:
        # o PNCP quer AAAAMMDD sem separador; o Balcão aceita ISO e traduz.
        # sem recorte, olha os últimos 7 dias; a fonte publica milhares por dia
        hoje = date.today()
        de = params.get("de") or (hoje - timedelta(days=7)).isoformat()
        ate = params.get("ate") or hoje.isoformat()
        de_d, ate_d = para_data(str(de)), para_data(str(ate))
        if de_d is None or ate_d is None or de_d > ate_d:
            raise ParametroInvalido(recurso, ["de", "ate"], ["datas AAAA-MM-DD, de <= ate"])
        return de_d.strftime("%Y%m%d"), ate_d.strftime("%Y%m%d")

    def _modalidade(self, recurso: str, valor: Any) -> int:
        if valor is None:
            return MODALIDADES["pregao-eletronico"]  # a modalidade mais comum
        chave = str(valor).strip().lower()
        if chave in MODALIDADES:
            return MODALIDADES[chave]
        if chave.isdigit() and int(chave) in MODALIDADES.values():
            return int(chave)
        raise ParametroInvalido(recurso, ["modalidade"], sorted(MODALIDADES))

    def _pagina(self, recurso: str, params: dict) -> int:
        valor = params.get("pagina", 1)
        if not str(valor).isdigit() or int(valor) < 1:
            raise ParametroInvalido(recurso, ["pagina"], ["pagina numérica >= 1"])
        return int(valor)

    def _valida(self, recurso: str, params: dict, aceitos: set) -> None:
        invalidos = sorted(set(params) - aceitos)
        if invalidos:
            raise ParametroInvalido(recurso, invalidos, sorted(aceitos))


def _decimal(valor: Any) -> Decimal | None:
    if valor is None:
        return None
    try:
        return Decimal(str(valor))
    except ArithmeticError:
        return None
