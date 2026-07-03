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
    valor_documento: Decimal | None = None  # o valor de face da nota
    valor_glosa: Decimal | None = None  # a parte que a própria Câmara cortou
    url_documento: str | None = None  # o PDF da nota fiscal


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


class Acao(BaseModel):
    """Uma ação ou índice da B3 — preço de mercado com o atraso do plano
    gratuito da fonte (~15 minutos)."""

    fonte: str = "b3"
    ticker: str  # PETR4, VALE3, IBOV
    nome: str | None = None
    preco: Decimal  # pontos, no caso de índice
    variacao_pct: float | None = None  # no dia
    abertura: Decimal | None = None
    maxima: Decimal | None = None
    minima: Decimal | None = None
    fechamento_anterior: Decimal | None = None
    moeda: str | None = None  # BRL; None em índice
    atualizado: str | None = None


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


class DoacaoAgregada(BaseModel):
    """Doações de campanha somadas por candidato, partido, doador ou origem —
    a prestação de contas do TSE, agregada."""

    fonte: str = "tse"
    ano: int
    uf: str
    nivel: str  # candidato, partido, doador ou origem
    nome: str
    detalhe: str | None = None  # partido/cargo do candidato, documento do doador
    total: Decimal  # R$
    doacoes: int


class Materia(BaseModel):
    """Uma matéria legislativa do Senado (PL, PEC...) na API nova de
    processos — o que está tramitando e onde parou."""

    fonte: str = "senado"
    id: int
    identificacao: str  # "PL 199/2026"
    ementa: str
    autor: str | None = None
    apresentada_em: date | None = None
    situacao: str | None = None
    situacao_em: date | None = None
    atualizada_em: date | None = None
    tramitando: bool = False
    url: str | None = None


class Processo(BaseModel):
    """A capa de um processo judicial no DataJud: classe, assuntos, órgão e o
    último andamento. Só metadados públicos — partes e conteúdo não vêm
    (segredo de justiça e LGPD)."""

    fonte: str = "datajud"
    tribunal: str
    numero: str
    classe: str | None = None
    assuntos: list[str] = []
    orgao: str | None = None
    municipio_ibge: int | None = None
    grau: str | None = None
    ajuizado_em: date | None = None
    ultima_atualizacao: date | None = None
    movimentos: int = 0
    ultimo_movimento: str | None = None
    ultimo_movimento_em: date | None = None


class ClasseProcessual(BaseModel):
    """Quantos processos de uma classe existem num tribunal — o retrato do
    que mais se processa."""

    fonte: str = "datajud"
    tribunal: str
    classe: str
    processos: int


class PrecoCombustivel(BaseModel):
    """Preço médio de um combustível num estado ou município, agregado das
    coletas da ANP nos postos das últimas quatro semanas."""

    fonte: str = "anp"
    combustivel: str  # gasolina, etanol, diesel-s10...
    produto: str  # o nome oficial na fonte (GASOLINA ADITIVADA...)
    nivel: str  # estado ou municipio
    local: str  # "GO" ou "GOIÂNIA"
    uf: str | None = None
    preco_medio: Decimal
    preco_minimo: Decimal
    preco_maximo: Decimal
    coletas: int  # quantos preços de posto entraram na média
    unidade: str  # "R$ / litro", "R$ / 13kg"...


class TituloPublico(BaseModel):
    """Um título do Tesouro Direto na última data publicada: a taxa e o preço
    unitário de compra e venda. O nome comercial (Tesouro Selic 2029) é
    montado a partir do tipo + ano de vencimento."""

    fonte: str = "tesourodireto"
    nome: str  # "Tesouro Selic 2029"
    tipo: str  # Tesouro Selic, Tesouro Prefixado, Tesouro IPCA+...
    vencimento: date
    data: date  # a data-base do preço
    taxa_compra: Decimal | None = None  # % a.a.
    taxa_venda: Decimal | None = None
    pu_compra: Decimal | None = None  # preço unitário, R$
    pu_venda: Decimal | None = None


class BalancaMensal(BaseModel):
    """Um mês da balança comercial: quanto o Brasil exportou, importou e o
    saldo, em dólares FOB."""

    fonte: str = "comex"
    mes: str  # "2026-05"
    exportacoes: Decimal  # US$ FOB
    importacoes: Decimal
    saldo: Decimal


class LinhaComercio(BaseModel):
    """Uma linha de ranking do comércio exterior — por país, UF ou produto —
    num fluxo (exportação ou importação) e período."""

    fonte: str = "comex"
    fluxo: str  # exportacao | importacao
    dimensao: str  # pais | uf | produto
    nome: str  # China, São Paulo, "Combustíveis minerais..."
    codigo: str | None = None  # código do capítulo NCM, quando produto
    valor_fob: Decimal  # US$
    peso_kg: Decimal | None = None


class AlertaDengue(BaseModel):
    """Uma semana epidemiológica de um município no InfoDengue: casos
    notificados, a estimativa corrigida (nowcast) e o nível de alerta do
    modelo — de verde (1) a vermelho (4)."""

    fonte: str = "infodengue"
    municipio: str
    ibge: int
    doenca: str  # dengue, zika ou chikungunya
    semana: int  # AAAASS (ano + semana epidemiológica)
    inicio_semana: date | None = None
    casos: int | None = None  # notificados (consolida com atraso)
    casos_estimados: float | None = None  # nowcast do modelo
    incidencia_100k: float | None = None
    rt: float | None = None  # número de reprodução (>1 = crescendo)
    nivel: int  # 1 verde, 2 amarelo, 3 laranja, 4 vermelho
    alerta: str  # o nível por extenso
    populacao: int | None = None


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


class PerfilDeputado(BaseModel):
    """O deputado por inteiro — o que a lista não conta: formação, origem,
    gabinete pra cobrar e redes pra acompanhar."""

    fonte: str = "camara"
    id: int
    nome: str
    nome_civil: str | None = None
    partido: str | None = None
    uf: str | None = None
    situacao: str | None = None
    condicao: str | None = None  # Titular ou Suplente
    nascimento: date | None = None
    naturalidade: str | None = None  # "Cidade · UF"
    escolaridade: str | None = None
    email: str | None = None
    telefone_gabinete: str | None = None
    gabinete: str | None = None  # "prédio 4, sala 617"
    site: str | None = None
    redes: list[str] = []
    foto: str | None = None


class Discurso(BaseModel):
    fonte: str = "camara"
    deputado_id: int
    data: str | None = None  # dataHoraInicio, ISO
    tipo: str | None = None
    sumario: str | None = None
    transcricao: str | None = None  # texto integral do que foi dito
    evento: str | None = None
    url_video: str | None = None
    url_audio: str | None = None


class OrientacaoBancada(BaseModel):
    """Como cada partido/bloco (e o Governo/Oposição) orientou a bancada numa
    votação nominal. Cruzar com os votos revela quem seguiu e quem traiu."""

    fonte: str = "camara"
    votacao_id: str
    bancada: str  # sigla do partido/bloco ou "Governo"/"Oposição"/"Maioria"
    orientacao: str  # Sim, Não, Liberado...
    lideranca: str | None = None  # P = partido, B = bloco


class ItemCompra(BaseModel):
    """Um item de uma contratação do PNCP: o que exatamente está sendo
    comprado, em que quantidade e por quanto (estimado)."""

    fonte: str = "pncp"
    numero: int
    descricao: str
    quantidade: float | None = None
    unidade: str | None = None
    valor_unitario: Decimal | None = None
    valor_total: Decimal | None = None
    situacao: str | None = None
    tem_resultado: bool = False
    beneficio: str | None = None  # exclusivo ME/EPP etc.


class VencedorItem(BaseModel):
    fonte: str = "pncp"
    item: int
    fornecedor: str
    documento: str | None = None  # CNPJ/CPF, só dígitos
    porte: str | None = None
    valor_unitario: Decimal | None = None
    valor_total: Decimal | None = None
    quantidade: float | None = None
    desconto_pct: float | None = None
    situacao: str | None = None
    data: date | None = None


class DocumentoEmenda(BaseModel):
    """Um empenho/documento por trás de uma emenda parlamentar — o rastro
    concreto do dinheiro."""

    fonte: str = "transparencia"
    emenda: str  # código da emenda
    data: date | None = None
    fase: str | None = None  # Empenho, Liquidação, Pagamento
    documento: str | None = None
    documento_resumido: str | None = None
    especie: str | None = None
    tipo_emenda: str | None = None


class TaxaJurosBanco(BaseModel):
    """Uma linha do ranking oficial de juros do BCB: quanto cada banco cobra
    numa modalidade de crédito, no mês de referência."""

    fonte: str = "bacen"
    posicao: int
    instituicao: str
    modalidade: str
    mes: str | None = None  # "Mai-2026"
    taxa_mes: float | None = None  # % ao mês
    taxa_ano: float | None = None  # % ao ano


class FichaEmpresa(BaseModel):
    """A ficha cadastral de um CNPJ na Receita (via BrasilAPI)."""

    fonte: str = "brasilapi"
    cnpj: str
    razao_social: str
    nome_fantasia: str | None = None
    situacao: str | None = None
    natureza: str | None = None
    abertura: date | None = None
    atividade: str | None = None  # descrição do CNAE principal
    capital_social: Decimal | None = None
    municipio: str | None = None
    uf: str | None = None
    socios: list[str] = []


class ProposicaoResumo(BaseModel):
    """Uma proposição citada dentro de uma votação — o 'sobre o quê'."""

    fonte: str = "camara"
    id: int
    titulo: str  # "PEC 231/2019"
    ementa: str | None = None


class VotacaoCompleta(Votacao):
    """O detalhe que conta a história: o parecer votado e as proposições
    afetadas com ementa — 'Aprovado o Parecer' deixa de ser enigma."""

    parecer: str | None = None
    proposicoes: list[ProposicaoResumo] = []


class ProposicaoDetalhe(Proposicao):
    """O dossiê de um projeto: onde está, com quem, em que regime e o link
    pro texto integral."""

    ementa_detalhada: str | None = None
    situacao: str | None = None  # "Transformado em Norma Jurídica"
    tramitacao: str | None = None
    orgao: str | None = None  # onde está agora (sigla)
    regime: str | None = None
    despacho: str | None = None
    url_inteiro_teor: str | None = None
    keywords: str | None = None


class ArquivoCompra(BaseModel):
    """Um documento publicado junto da contratação no PNCP (edital, anexos)."""

    fonte: str = "pncp"
    titulo: str
    url: str


class ObraPublica(BaseModel):
    """Uma obra/projeto de investimento federal no Obrasgov — inclusive as
    paradas, que são a pauta."""

    fonte: str = "obrasgov"
    id: str
    nome: str
    descricao: str | None = None
    uf: str | None = None
    endereco: str | None = None
    situacao: str | None = None  # Paralisada, Em execução, Concluída...
    especie: str | None = None  # Construção, Reforma...
    valor_previsto: Decimal | None = None  # a fonte deixa vazio com frequência
    inicio_previsto: date | None = None
    fim_previsto: date | None = None
    inicio_efetivo: date | None = None
    fim_efetivo: date | None = None
    executor: str | None = None  # quem toca a obra (ex: FNDE)
    executor_codigo: str | None = None  # em repasse a ente, é o CNPJ sem zeros à esquerda
    empregos: int | None = None
    populacao_beneficiada: int | None = None
    atrasada: bool = False  # fim previsto no passado e obra não concluída


class EmpenhoObra(BaseModel):
    """Um empenho da execução financeira de uma obra — dinheiro que já saiu."""

    fonte: str = "obrasgov"
    obra: str  # idUnico
    favorecido: str | None = None
    valor: Decimal | None = None
    natureza: str | None = None
    nota: str | None = None  # numeroNotaEmpenhoGerada, quando vem
    ug: str | None = None


class DocumentoSiafi(BaseModel):
    """O detalhe de um documento do SIAFI (empenho/liquidação/pagamento) no
    Portal da Transparência — é aqui que o favorecido aparece com CNPJ."""

    fonte: str = "transparencia"
    documento: str
    fase: str | None = None
    data: date | None = None
    favorecido: str | None = None
    favorecido_doc: str | None = None  # CNPJ/CPF, só dígitos
    uf_favorecido: str | None = None
    valor: Decimal | None = None
    orgao: str | None = None
    modalidade: str | None = None  # ex: "40 - Transferências a Municípios"
    autor_emenda: str | None = None  # quando o dinheiro veio de emenda
    observacao: str | None = None


class DiarioOficial(BaseModel):
    """Um diário oficial municipal achado pela busca do Querido Diário,
    com os trechos onde o termo aparece."""

    fonte: str = "diarios"
    municipio: str
    uf: str | None = None
    data: date | None = None
    edicao: str | None = None
    extra: bool = False
    trechos: list[str] = []
    url: str  # o PDF oficial
    url_texto: str | None = None  # o texto puro extraído


class CidadeDiario(BaseModel):
    """Um município no radar do Querido Diário (cobertura)."""

    fonte: str = "diarios"
    ibge: int
    nome: str
    uf: str | None = None


class CensoCidade(BaseModel):
    """O retrato do Censo 2022 pra um município: gente e moradia."""

    fonte: str = "sidra"
    municipio: str
    ibge: int | None = None
    ano: int  # ano de referência do Censo
    populacao: int | None = None
    variacao_desde_2010: int | None = None
    crescimento_aa_pct: float | None = None  # taxa geométrica anual
    domicilios: int | None = None
    moradores_por_domicilio: float | None = None


class PibCidade(BaseModel):
    """O PIB municipal (contas do IBGE, publicadas com ~2 anos de defasagem)."""

    fonte: str = "sidra"
    municipio: str
    ibge: int | None = None
    ano: int
    pib: Decimal | None = None  # em reais (a fonte fala em mil reais)


class SafraMensal(BaseModel):
    """A estimativa do LSPA/IBGE pra safra em curso — revisada todo mês."""

    fonte: str = "sidra"
    produto: str
    mes: str  # AAAAMM do levantamento
    localidade: str
    area_plantada_ha: float | None = None
    producao_t: float | None = None
    rendimento_kg_ha: float | None = None


class Abate(BaseModel):
    """Quantos animais o Brasil abateu no trimestre (pesquisa do IBGE)."""

    fonte: str = "sidra"
    tipo: str  # bovino, suino, frango
    trimestre: str
    animais: float | None = None
    peso_kg: float | None = None


class Leite(BaseModel):
    fonte: str = "sidra"
    trimestre: str
    localidade: str = "Brasil"
    litros: float | None = None
    preco_medio: float | None = None  # R$/litro pago ao produtor


class SafraConab(BaseModel):
    """Uma linha do levantamento mensal de grãos da CONAB."""

    fonte: str = "conab"
    ano_agricola: str  # "2025/26"
    levantamento: str  # "9º LEV"
    produto: str
    uf: str | None = None  # None = Brasil (somado)
    area_mil_ha: float | None = None
    producao_mil_t: float | None = None
    produtividade: float | None = None  # t/ha


class PrecoAgro(BaseModel):
    """Preço médio de mercado apurado pela CONAB, normalizado por kg."""

    fonte: str = "conab"
    produto: str
    uf: str
    nivel: str | None = None  # ex: preço pago ao produtor
    periodo: str  # AAAA-MM
    valor_kg: float | None = None


class ContratoFederal(BaseModel):
    """Um contrato do governo federal com um CNPJ/CPF (Transparência)."""

    fonte: str = "transparencia"
    objeto: str
    orgao: str | None = None
    valor: Decimal | None = None
    inicio: date | None = None
    fim: date | None = None
    situacao: str | None = None
    modalidade: str | None = None


class Reservatorio(BaseModel):
    """Um reservatório monitorado pela ANA (SIN, Nordeste ou Cantareira)."""

    fonte: str = "ana"
    codigo: str
    nome: str
    sistema: str  # sin | nordeste | cantareira
    uf: str | None = None  # a ANA só informa nos açudes do Nordeste


class MedicaoReservatorio(BaseModel):
    """Uma medição diária de reservatório: quanto tem e quanto entra/sai."""

    fonte: str = "ana"
    codigo: str
    reservatorio: str
    sistema: str | None = None
    data: date | None = None
    volume_util_pct: float | None = None
    volume_hm3: float | None = None  # só a série do Cantareira informa
    cota: float | None = None  # nível da água, em metros
    afluencia: float | None = None  # m³/s entrando
    defluencia: float | None = None  # m³/s saindo


class RankingReclamacao(BaseModel):
    """Uma instituição no ranking oficial de reclamações do Banco Central."""

    fonte: str = "bacen"
    posicao: int | None = None  # só quem tem índice entra na fila
    instituicao: str
    indice: float | None = None  # reclamações procedentes por 1 milhão de clientes
    top15: bool = False  # o BC destaca os 15 grandes (mais de 4 mi de clientes)
    reclamacoes_procedentes: int | None = None
    reclamacoes_respondidas: int | None = None
    reclamacoes_analisadas: int | None = None
    clientes: int | None = None
    periodo: str


class SorteioLoteria(BaseModel):
    """Um concurso das Loterias CAIXA, com rateio e a estimativa do próximo."""

    fonte: str = "loterias"
    jogo: str
    nome_jogo: str
    concurso: int
    data: date | None = None
    dezenas: list[str] = []
    dezenas_2: list[str] | None = None  # a Dupla Sena sorteia duas vezes
    extra: str | None = None  # Mês da Sorte / Time do Coração
    acumulado: bool = False
    premios: list[dict] = []  # faixa, ganhadores, valor
    cidades_ganhadoras: list[dict] = []
    arrecadacao: Decimal | None = None
    acumulado_proximo: Decimal | None = None
    estimativa_proximo: Decimal | None = None
    data_proximo: date | None = None


class FrequenciaNome(BaseModel):
    """Quantos brasileiros nasceram com um nome numa década (Censo 2010)."""

    fonte: str = "ibge"
    nome: str
    decada: str  # "1990" ou "até 1930"
    frequencia: int


class NomeNoEstado(BaseModel):
    """A força de um nome em cada estado, por 100 mil habitantes."""

    fonte: str = "ibge"
    nome: str
    uf: str
    frequencia: int
    por_100k: float | None = None


class RankingNome(BaseModel):
    """Uma posição no ranking dos nomes mais comuns do Brasil (Censo 2010)."""

    fonte: str = "ibge"
    posicao: int
    nome: str
    frequencia: int
