"""Schemas normalizados do Balcão. Toda fonte responde com estes modelos,
nao importa o formato que ela use por dentro."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class Deputado(BaseModel):
    fonte: str = "camara"
    id: int
    nome: str
    partido: str | None = None
    uf: str | None = None
    legislatura: int | None = None
    email: str | None = None
    foto: str | None = None
    situacao: str | None = None


class Despesa(BaseModel):
    fonte: str = "camara"
    deputado_id: int
    ano: int
    mes: int
    tipo: str
    fornecedor: str
    fornecedor_doc: str | None = None  # cnpj ou cpf, so digitos
    data: date | None = None
    valor: Decimal  # valorLiquido, o que foi de fato reembolsado
    url_documento: str | None = None


class Votacao(BaseModel):
    fonte: str = "camara"
    id: str
    data: date | None = None
    orgao: str | None = None
    descricao: str
    aprovada: bool | None = None


class Proposicao(BaseModel):
    fonte: str = "camara"
    id: int
    tipo: str  # PL, PEC, MPV e afins
    numero: int | None = None
    ano: int | None = None
    ementa: str


class Senador(BaseModel):
    fonte: str = "senado"
    id: int
    nome: str
    partido: str | None = None
    uf: str | None = None
    email: str | None = None
    foto: str | None = None


class PontoSerie(BaseModel):
    fonte: str = "bacen"
    serie: int
    nome: str | None = None
    data: date | None = None
    valor: Decimal


class Estado(BaseModel):
    fonte: str = "ibge"
    id: int
    sigla: str
    nome: str
    regiao: str | None = None


class Municipio(BaseModel):
    fonte: str = "ibge"
    id: int
    nome: str
    uf: str | None = None
    regiao: str | None = None


class FinancaEstado(BaseModel):
    fonte: str = "tesouro"
    uf: str
    ano: int
    populacao: int | None = None
    receita_total: Decimal
    receita_impostos: Decimal | None = None  # quanto vem de impostos
    despesa_total: Decimal


class DespesaFuncao(BaseModel):
    fonte: str = "tesouro"
    uf: str
    ano: int
    funcao: str  # saúde, educação, segurança...
    valor: Decimal
