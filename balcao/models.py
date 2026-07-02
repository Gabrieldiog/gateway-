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


class IndicadorEconomico(BaseModel):
    """Uma linha do painel de custo de vida: o valor mais recente de uma série
    do BACEN, já com rótulo e unidade prontos pra exibir (o /serie cru só dá o
    número, aqui vem 'IPCA (12 meses) = 4,72 % ao ano')."""

    fonte: str = "bacen"
    chave: str  # ipca, igpm, selic, dolar...
    serie: int  # código da série no SGS
    nome: str  # rótulo legível
    unidade: str  # "% no mês", "% ao ano", "% ao dia", "R$"
    data: date | None = None
    valor: Decimal


class ExpectativaMercado(BaseModel):
    """O que o mercado espera para um indicador num ano de referência — a
    projeção do Boletim Focus (BACEN), na coleta (semana) mais recente. É o
    olhar pra frente que o /serie do BACEN, retrospectivo, não dá."""

    fonte: str = "focus"
    indicador: str  # IPCA, Selic, Câmbio, PIB Total, IGP-M
    referencia: str  # ano-alvo da projeção, ex "2026"
    unidade: str  # "%" ou "R$" (câmbio)
    data: date | None = None  # data da coleta (o Focus é semanal)
    mediana: float | None = None
    media: float | None = None
    minimo: float | None = None
    maximo: float | None = None
    desvio_padrao: float | None = None
    respondentes: int | None = None


class Cotacao(BaseModel):
    """Cotação de câmbio/cripto quase em tempo real (preço de mercado)."""

    fonte: str = "cotacoes"
    par: str  # "USD/BRL"
    moeda: str  # "USD"
    nome: str | None = None
    compra: Decimal  # bid
    venda: Decimal | None = None  # ask
    variacao_pct: float | None = None  # variação no dia, em %
    maxima: Decimal | None = None
    minima: Decimal | None = None
    atualizado: str | None = None  # quando a fonte registrou (data/hora)


class Emenda(BaseModel):
    """Uma emenda parlamentar: dinheiro que um congressista destinou do
    orçamento. Os valores chegam da fonte em formato brasileiro ("8.000,00")
    e saem daqui como Decimal."""

    fonte: str = "transparencia"
    codigo: str
    ano: int
    tipo: str | None = None  # individual, bancada...
    autor: str
    localidade: str | None = None  # "CUIABÁ - MT" — onde o dinheiro vai
    funcao: str | None = None  # saúde, educação...
    valor_empenhado: Decimal | None = None
    valor_liquidado: Decimal | None = None
    valor_pago: Decimal | None = None


class Sancao(BaseModel):
    """Empresa ou pessoa punida pelo poder público — impedida de contratar
    (CEIS) ou punida pela Lei Anticorrupção (CNEP)."""

    fonte: str = "transparencia"
    cadastro: str  # CEIS ou CNEP
    sancionado: str
    documento: str | None = None  # CPF/CNPJ formatado
    tipo: str | None = None  # a sanção em si
    orgao: str | None = None  # quem puniu
    uf: str | None = None
    esfera: str | None = None  # FEDERAL, ESTADUAL, MUNICIPAL
    inicio: date | None = None
    fim: date | None = None


class BeneficioSocial(BaseModel):
    """Total pago por um programa social num município num mês (quantos
    beneficiários e quanto dinheiro entrou)."""

    fonte: str = "transparencia"
    programa: str  # "Novo Bolsa Família"
    municipio: str
    uf: str | None = None
    ibge: int | None = None
    referencia: date | None = None  # o mês da folha
    beneficiarios: int | None = None
    valor: Decimal


class Licitacao(BaseModel):
    """Uma contratação pública divulgada no PNCP: o que um órgão quer comprar,
    por qual modalidade e por quanto (estimado)."""

    fonte: str = "pncp"
    numero_controle: str  # id nacional da compra no PNCP
    ano: int
    orgao: str
    cnpj_orgao: str | None = None
    esfera: str | None = None  # federal, estadual, municipal
    municipio: str | None = None
    uf: str | None = None
    modalidade: str | None = None  # Pregão - Eletrônico, Dispensa...
    objeto: str
    valor_estimado: Decimal | None = None
    situacao: str | None = None
    publicada_em: date | None = None
    propostas_ate: date | None = None  # até quando aceita proposta


class ContratoPublico(BaseModel):
    """Um contrato assinado e publicado no PNCP: quem contratou, quem fornece
    e por quanto."""

    fonte: str = "pncp"
    numero_controle: str
    ano: int
    orgao: str
    municipio: str | None = None
    uf: str | None = None
    fornecedor: str
    fornecedor_doc: str | None = None  # CNPJ/CPF, só dígitos
    objeto: str
    valor: Decimal | None = None  # valor global do contrato
    assinado_em: date | None = None
    vigencia_inicio: date | None = None
    vigencia_fim: date | None = None


class Queimada(BaseModel):
    """Focos de incêndio agregados por estado ou bioma num dia. Vem do INPE
    (Programa Queimadas), que detecta os focos por satélite e atualiza o
    arquivo do dia ao longo das horas."""

    fonte: str = "inpe"
    data: date
    nivel: str  # estado, bioma ou municipio
    nome: str  # "MATO GROSSO", "Cerrado"...
    focos: int  # quantos focos detectados
    frp_total: float | None = None  # soma da potência radiativa do fogo (MW)


class GeracaoEnergia(BaseModel):
    """Foto da geração de energia num instante — potência por fonte, carga e o
    percentual renovável. Vem do ONS quase em tempo real (atualiza a cada
    minuto). `regiao` é "SIN" (o Brasil todo) ou um subsistema."""

    fonte: str = "ons"
    instante: str  # ISO do dado, ex "2026-07-01T20:48:00-03:00"
    regiao: str  # SIN, Sudeste/Centro-Oeste, Sul, Nordeste, Norte
    geracao_total: float  # MW
    hidraulica: float
    termica: float
    eolica: float
    solar: float
    nuclear: float
    carga: float | None = None  # demanda verificada (MW)
    renovavel_pct: float | None = None  # (hidráulica + eólica + solar) / total


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


class VotoDeputado(BaseModel):
    fonte: str = "camara"
    votacao_id: str
    voto: str  # Sim, Não, Abstenção, Obstrução
    deputado_id: int
    deputado: str
    partido: str | None = None
    uf: str | None = None
    data: date | None = None  # quando o voto foi registrado


class VotoSenador(BaseModel):
    """Um voto de um senador numa votação — o histórico vem inteiro numa
    chamada só, diferente da Câmara (que é por votação)."""

    fonte: str = "senado"
    votacao_id: str
    data: date | None = None
    voto: str  # Sim, Não, Abstenção; "Votou" (secreta), "Missão"/"Ausente" etc.
    descricao: str  # o assunto da matéria (ementa)
    materia: str | None = None  # ex: PLP 189/2019
    aprovada: bool | None = None
    secreta: bool = False


class Estabelecimento(BaseModel):
    fonte: str = "sus"
    cnes: int
    nome: str
    tipo: str | None = None  # descrição do tipo (HOSPITAL GERAL, POSTO DE SAUDE...)
    tipo_codigo: int | None = None
    esfera: str | None = None  # MUNICIPAL, ESTADUAL, FEDERAL, PRIVADA
    cnpj: str | None = None
    municipio_id: int | None = None
    uf: str | None = None
    bairro: str | None = None
    endereco: str | None = None
    telefone: str | None = None
    email: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class FinancaEnte(BaseModel):
    """Panorama fiscal de um ente — União, estado ou município. A mesma fonte
    (SICONFI) responde pros três níveis, só muda o código IBGE consultado."""

    fonte: str = "tesouro"
    nivel: str  # uniao, estado ou municipio
    ente: str  # "Brasil", "SP", "Goiânia" — nome legível do ente
    uf: str | None = None  # None na União
    ibge: int | None = None  # código IBGE do ente
    ano: int
    populacao: int | None = None
    receita_total: Decimal
    receita_impostos: Decimal | None = None  # só impostos (IR, ICMS, ISS...)
    receita_contribuicoes: Decimal | None = None  # INSS, COFINS, PIS, CSLL...
    # arrecadação tributária = impostos + taxas + contribuições; é o número que
    # bate com o "arrecadação total" das manchetes (impostos sozinho é menor)
    arrecadacao_total: Decimal | None = None
    despesa_total: Decimal


class DespesaFuncao(BaseModel):
    fonte: str = "tesouro"
    nivel: str  # uniao, estado ou municipio
    ente: str
    uf: str | None = None
    ibge: int | None = None
    ano: int
    funcao: str  # saúde, educação, segurança...
    valor: Decimal


class Imposto(BaseModel):
    """Quanto um ente arrecadou de um imposto específico. A sigla é derivada
    do código de natureza da receita do SICONFI (padrão nacional da STN)."""

    fonte: str = "tesouro"
    nivel: str  # uniao, estado ou municipio
    ente: str
    uf: str | None = None
    ibge: int | None = None
    ano: int
    sigla: str  # IPTU, ISS, ICMS, IPVA, IR, IPI, II, IE, IOF, ITR, ITBI, ITCMD
    nome: str
    valor: Decimal


class IndicadorAgro(BaseModel):
    fonte: str = "sidra"
    localidade: str  # nome do estado ou município
    localidade_id: int | None = None  # código IBGE
    ano: int
    item: str  # soja, milho, Bovino... (cultura ou rebanho)
    variavel: str  # quantidade produzida, área plantada, efetivo do rebanho...
    valor: float | None = None  # None quando a fonte não tem o dado (vem "-" ou "..")
    unidade: str | None = None  # Toneladas, Hectares, Cabeças...


class DatasetCKAN(BaseModel):
    fonte: str  # aneel, mme, antt... (cada portal CKAN é uma fonte)
    id: str
    nome: str  # slug do conjunto
    titulo: str
    organizacao: str | None = None
    atualizado: str | None = None
    # recursos do conjunto; datastore=True significa que dá pra puxar linha via /dados/{id}
    recursos: list[dict] = []


class SerieIpea(BaseModel):
    fonte: str = "ipeadata"
    codigo: str  # SERCODIGO
    nome: str
    unidade: str | None = None
    periodicidade: str | None = None  # Mensal, Anual...
    fonte_dados: str | None = None  # quem produz o dado original (IBGE, BCB...)
    base: str | None = None  # Macroeconômico, Regional, Social
    ativa: bool = True


class PontoIpea(BaseModel):
    fonte: str = "ipeadata"
    codigo: str
    data: date | None = None
    valor: float | None = None
    territorio: str | None = None  # quando a série é regional
