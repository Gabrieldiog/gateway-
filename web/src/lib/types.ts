// espelham os schemas normalizados do Balcao (balcao/models.py)

export interface NormalizedResponse<T> {
  fonte: string;
  recurso: string;
  dados: T[];
  total: number | null;
  meta: Record<string, unknown>;
}

export interface Deputado {
  fonte: string;
  id: number;
  nome: string;
  partido: string | null;
  uf: string | null;
  legislatura: number | null;
  email: string | null;
  foto: string | null;
  situacao: string | null;
}

export interface Despesa {
  fonte: string;
  deputado_id: number;
  ano: number;
  mes: number;
  tipo: string;
  fornecedor: string;
  fornecedor_doc: string | null;
  data: string | null;
  valor: string;
  valor_documento: string | null; // valor de face da nota
  valor_glosa: string | null; // o que a própria Câmara cortou
  url_documento: string | null; // o PDF da nota fiscal
}

export interface Senador {
  fonte: string;
  id: number;
  nome: string;
  partido: string | null;
  uf: string | null;
  email: string | null;
  foto: string | null;
}

export interface PontoSerie {
  fonte: string;
  serie: number;
  nome: string | null;
  data: string | null;
  valor: string;
}

// ação ou índice da B3 (/v1/b3/acoes/...) — ~15 min de atraso no plano free
export interface Acao {
  fonte: string;
  ticker: string; // IBOV, PETR4...
  nome: string | null;
  preco: string;
  variacao_pct: number | null;
  abertura: string | null;
  maxima: string | null;
  minima: string | null;
  fechamento_anterior: string | null;
  moeda: string | null; // null em índice (pontos)
  atualizado: string | null;
}

export interface Cotacao {
  fonte: string;
  par: string; // "USD/BRL"
  moeda: string; // "USD"
  nome: string | null;
  compra: string;
  venda: string | null;
  variacao_pct: number | null;
  maxima: string | null;
  minima: string | null;
  atualizado: string | null;
}

// uma linha do painel /v1/bacen/inflacao — o valor mais recente de cada série
export interface IndicadorEconomico {
  fonte: string;
  chave: string; // ipca, ipca12m, igpm, selic, dolar...
  serie: number;
  nome: string; // "IPCA (12 meses)"
  unidade: string; // "% no mês", "% ao ano", "% ao dia", "R$"
  data: string | null;
  valor: string;
}

// uma linha do painel /v1/focus/painel — o que o mercado espera pra um ano
export interface ExpectativaMercado {
  fonte: string;
  indicador: string; // IPCA, Selic, Câmbio, PIB Total, IGP-M
  referencia: string; // ano-alvo, "2026"
  unidade: string; // "%" ou "R$"
  data: string | null; // data da coleta (semanal)
  mediana: number | null;
  media: number | null;
  minimo: number | null;
  maximo: number | null;
  desvio_padrao: number | null;
  respondentes: number | null;
}

export interface Estado {
  fonte: string;
  id: number;
  sigla: string;
  nome: string;
  regiao: string | null;
}

// emenda parlamentar (/v1/transparencia/emendas) — valores já normalizados
export interface Emenda {
  fonte: string;
  codigo: string;
  ano: number;
  tipo: string | null;
  autor: string;
  localidade: string | null;
  funcao: string | null;
  valor_empenhado: string | null;
  valor_liquidado: string | null;
  valor_pago: string | null;
}

// punição em vigor (/v1/transparencia/sancoes) — CEIS ou CNEP
export interface Sancao {
  fonte: string;
  cadastro: string; // CEIS | CNEP
  sancionado: string;
  documento: string | null;
  tipo: string | null;
  orgao: string | null;
  uf: string | null;
  esfera: string | null;
  inicio: string | null;
  fim: string | null;
}

// folha de um programa social num município (/v1/transparencia/bolsa-familia)
export interface BeneficioSocial {
  fonte: string;
  programa: string;
  municipio: string;
  uf: string | null;
  ibge: number | null;
  referencia: string | null;
  beneficiarios: number | null;
  valor: string;
}

// uma contratação divulgada no PNCP (/v1/pncp/licitacoes)
export interface Licitacao {
  fonte: string;
  numero_controle: string;
  ano: number;
  orgao: string;
  cnpj_orgao: string | null;
  esfera: string | null;
  municipio: string | null;
  uf: string | null;
  modalidade: string | null;
  objeto: string;
  valor_estimado: string | null;
  situacao: string | null;
  publicada_em: string | null;
  propostas_ate: string | null;
}

// um contrato assinado no PNCP (/v1/pncp/contratos)
export interface ContratoPublico {
  fonte: string;
  numero_controle: string;
  ano: number;
  orgao: string;
  municipio: string | null;
  uf: string | null;
  fornecedor: string;
  fornecedor_doc: string | null;
  objeto: string;
  valor: string | null;
  assinado_em: string | null;
  vigencia_inicio: string | null;
  vigencia_fim: string | null;
}

// preço agregado de um combustível (/v1/anp/precos) — média das coletas
export interface PrecoCombustivel {
  fonte: string;
  combustivel: string;
  produto: string;
  nivel: string; // estado | municipio
  local: string;
  uf: string | null;
  preco_medio: string;
  preco_minimo: string;
  preco_maximo: string;
  coletas: number;
  unidade: string;
}

// um título do Tesouro Direto na última data publicada (/v1/tesourodireto/titulos)
export interface TituloPublico {
  fonte: string;
  nome: string; // "Tesouro Selic 2029"
  tipo: string;
  vencimento: string;
  data: string;
  taxa_compra: string | null;
  taxa_venda: string | null;
  pu_compra: string | null;
  pu_venda: string | null;
}

// uma semana epidemiológica de um município (/v1/infodengue/alertas)
export interface AlertaDengue {
  fonte: string;
  municipio: string;
  ibge: number;
  doenca: string;
  semana: number; // AAAASS
  inicio_semana: string | null;
  casos: number | null;
  casos_estimados: number | null;
  incidencia_100k: number | null;
  rt: number | null;
  nivel: number; // 1..4
  alerta: string; // verde..vermelho
  populacao: number | null;
}

// um mês da balança comercial (/v1/comex/balanca), US$ FOB
export interface BalancaMensal {
  fonte: string;
  mes: string; // "2026-05"
  exportacoes: string;
  importacoes: string;
  saldo: string;
}

// linha de ranking do comércio exterior (/v1/comex/ranking/{dim})
export interface LinhaComercio {
  fonte: string;
  fluxo: string; // exportacao | importacao
  dimensao: string; // pais | uf | produto
  nome: string;
  codigo: string | null;
  valor_fob: string;
  peso_kg: string | null;
}

// focos de incêndio agregados por estado/bioma (/v1/inpe/queimadas)
export interface Queimada {
  fonte: string;
  data: string;
  nivel: string; // estado | bioma | municipio
  nome: string;
  focos: number;
  frp_total: number | null;
}

// foto da geração do SIN num instante (/v1/ons/geracao) — MW por fonte
export interface GeracaoEnergia {
  fonte: string;
  instante: string;
  regiao: string; // SIN ou o subsistema
  geracao_total: number;
  hidraulica: number;
  termica: number;
  eolica: number;
  solar: number;
  nuclear: number;
  carga: number | null;
  renovavel_pct: number | null;
}

export interface Municipio {
  fonte: string;
  id: number;
  nome: string;
  uf: string | null;
  regiao: string | null;
}

export interface Votacao {
  fonte: string;
  id: string;
  data: string | null;
  orgao: string | null;
  descricao: string;
  aprovada: boolean | null;
}

export interface VotoDeputado {
  fonte: string;
  votacao_id: string;
  voto: string; // Sim, Não, Abstenção, Obstrução
  deputado_id: number;
  deputado: string;
  partido: string | null;
  uf: string | null;
  data: string | null;
}

export interface Estabelecimento {
  fonte: string;
  cnes: number;
  nome: string;
  tipo: string | null;
  tipo_codigo: number | null;
  esfera: string | null;
  cnpj: string | null;
  municipio_id: number | null;
  uf: string | null;
  bairro: string | null;
  endereco: string | null;
  telefone: string | null;
  email: string | null;
  latitude: number | null;
  longitude: number | null;
}

export interface FinancaEnte {
  fonte: string;
  nivel: string; // uniao | estado | municipio
  ente: string; // "Brasil", "SP", "Goiânia"
  uf: string | null;
  ibge: number | null;
  ano: number;
  populacao: number | null;
  receita_total: string;
  receita_impostos: string | null; // só impostos
  receita_contribuicoes: string | null; // INSS, COFINS, PIS...
  arrecadacao_total: string | null; // impostos + taxas + contribuições
  despesa_total: string;
}

export interface DespesaFuncao {
  fonte: string;
  nivel: string;
  ente: string;
  uf: string | null;
  ibge: number | null;
  ano: number;
  funcao: string;
  valor: string;
}

export interface Imposto {
  fonte: string;
  nivel: string;
  ente: string;
  uf: string | null;
  ibge: number | null;
  ano: number;
  sigla: string; // ISS, IPTU, ICMS, IPVA, IR, IPI, II, IE, IOF, ITR, ITBI, ITCMD, OUTROS
  nome: string;
  valor: string;
}

export interface FonteDado {
  nome: string;
  url: string;
  nota: string;
}

// resposta da rota unificada /v1/arrecadacao
export interface Arrecadacao {
  ente: FinancaEnte;
  ano: number;
  total_impostos: string | null;
  impostos: Imposto[];
  despesas: DespesaFuncao[];
  fonte?: FonteDado;
  meta: Record<string, unknown>;
}

export interface LinhaRanking {
  ente: string;
  uf: string;
  nivel: string;
  populacao: number | null;
  total_impostos: string;
  valor: string;
}

// resposta de /v1/arrecadacao/ranking
export interface Ranking {
  nivel: string; // estado | capital
  ano: number;
  imposto: string | null;
  por: string; // total | per_capita
  total_entes: number;
  ranking: LinhaRanking[];
}

export interface IndicadorAgro {
  fonte: string;
  localidade: string;
  localidade_id: number | null;
  ano: number;
  item: string;
  variavel: string;
  valor: number | null;
  unidade: string | null;
}

export interface SerieIpea {
  fonte: string;
  codigo: string;
  nome: string;
  unidade: string | null;
  periodicidade: string | null;
  fonte_dados: string | null;
  base: string | null;
  ativa: boolean;
}

export interface PontoIpea {
  fonte: string;
  codigo: string;
  data: string | null;
  valor: number | null;
  territorio: string | null;
}

export interface DatasetCKAN {
  fonte: string;
  id: string;
  nome: string;
  titulo: string;
  organizacao: string | null;
  atualizado: string | null;
  recursos: { id: string; nome: string; formato: string | null; datastore: boolean }[];
}

export interface ResultadoBusca {
  tipo_resultado: string;
  [campo: string]: unknown;
}

export interface BuscaOut {
  q: string;
  fontes_consultadas: string[];
  total: number;
  resultados: ResultadoBusca[];
  erros: Record<string, string>;
  meta: Record<string, unknown>;
}

export interface GastosOut {
  fonte: string;
  deputado: Deputado;
  ano: number;
  total_documentos: number;
  valor_total: string;
  por_tipo: Record<string, string>;
}

export interface VotoHistorico {
  votacao_id: string;
  data: string | null;
  descricao: string;
  aprovada: boolean | null;
  voto: string;
  materia?: string | null; // só no Senado (ex: PLP 189/2019)
  secreta?: boolean; // só no Senado
}

export interface VotosParlamentarOut {
  fonte: string;
  casa: "camara" | "senado";
  parlamentar: Deputado; // mesmo shape básico (nome, partido, uf)
  analisadas: number;
  total: number;
  votos: VotoHistorico[];
}

export interface Fonte {
  nome: string;
  base_url: string;
  precisa_chave: boolean;
  descricao: string;
  recursos: Record<string, string>;
}

export interface FontesOut {
  total: number;
  fontes: Fonte[];
}

export interface ErroBalcao {
  erro: string;
  detalhes?: Record<string, unknown>;
}

export interface PerfilDeputado {
  fonte: string;
  id: number;
  nome: string;
  nome_civil: string | null;
  partido: string | null;
  uf: string | null;
  situacao: string | null;
  condicao: string | null;
  nascimento: string | null;
  naturalidade: string | null;
  escolaridade: string | null;
  email: string | null;
  telefone_gabinete: string | null;
  gabinete: string | null;
  site: string | null;
  redes: string[];
  foto: string | null;
}

export interface Discurso {
  fonte: string;
  deputado_id: number;
  data: string | null;
  tipo: string | null;
  sumario: string | null;
  transcricao: string | null;
  evento: string | null;
  url_video: string | null;
  url_audio: string | null;
}

export interface OrientacaoBancada {
  fonte: string;
  votacao_id: string;
  bancada: string; // partido/bloco ou "Governo"/"Oposição"/"Maioria"
  orientacao: string; // Sim, Não, Liberado...
  lideranca: string | null;
}

export interface ItemCompra {
  fonte: string;
  numero: number;
  descricao: string;
  quantidade: number | null;
  unidade: string | null;
  valor_unitario: string | null;
  valor_total: string | null;
  situacao: string | null;
  tem_resultado: boolean;
  beneficio: string | null;
}

export interface VencedorItem {
  fonte: string;
  item: number;
  fornecedor: string;
  documento: string | null;
  porte: string | null;
  valor_unitario: string | null;
  valor_total: string | null;
  quantidade: number | null;
  desconto_pct: number | null;
  situacao: string | null;
  data: string | null;
}

export interface DocumentoEmenda {
  fonte: string;
  emenda: string;
  data: string | null;
  fase: string | null;
  documento: string | null;
  documento_resumido: string | null;
  especie: string | null;
  tipo_emenda: string | null;
}

export interface TaxaJurosBanco {
  fonte: string;
  posicao: number;
  instituicao: string;
  modalidade: string;
  mes: string | null; // início da janela de coleta
  taxa_mes: number | null;
  taxa_ano: number | null;
}

export interface FichaEmpresa {
  fonte: string;
  cnpj: string;
  razao_social: string;
  nome_fantasia: string | null;
  situacao: string | null;
  natureza: string | null;
  abertura: string | null;
  atividade: string | null;
  capital_social: string | null;
  municipio: string | null;
  uf: string | null;
  socios: string[];
}

export interface ContratoFederal {
  fonte: string;
  objeto: string;
  orgao: string | null;
  valor: string | null;
  inicio: string | null;
  fim: string | null;
  situacao: string | null;
  modalidade: string | null;
}

export interface VinculosEmpresa {
  fonte: string;
  cnpj: string;
  razao_social: string | null;
  nome_fantasia: string | null;
  vinculos: string[]; // as flags acesas
  flags: Record<string, boolean>;
}

export interface DiarioOficial {
  fonte: string;
  municipio: string;
  uf: string | null;
  data: string | null;
  edicao: string | null;
  extra: boolean;
  trechos: string[];
  url: string;
  url_texto: string | null;
}

export interface CensoCidade {
  fonte: string;
  municipio: string;
  ibge: number | null;
  ano: number;
  populacao: number | null;
  variacao_desde_2010: number | null;
  crescimento_aa_pct: number | null;
  domicilios: number | null;
  moradores_por_domicilio: number | null;
}

export interface PibCidade {
  fonte: string;
  municipio: string;
  ibge: number | null;
  ano: number;
  pib: string | null; // em reais
}

export interface SafraMensal {
  fonte: string;
  produto: string;
  mes: string; // AAAAMM do levantamento
  localidade: string;
  area_plantada_ha: number | null;
  producao_t: number | null;
  rendimento_kg_ha: number | null;
}

export interface Abate {
  fonte: string;
  tipo: string;
  trimestre: string;
  animais: number | null;
  peso_kg: number | null;
}

export interface Leite {
  fonte: string;
  trimestre: string;
  localidade: string;
  litros: number | null;
  preco_medio: number | null;
}

export interface SafraConab {
  fonte: string;
  ano_agricola: string;
  levantamento: string;
  produto: string;
  uf: string | null;
  area_mil_ha: number | null;
  producao_mil_t: number | null;
  produtividade: number | null;
}

export interface PrecoAgro {
  fonte: string;
  produto: string;
  uf: string;
  nivel: string | null;
  periodo: string; // AAAA-MM
  valor_kg: number | null;
}

export interface ProposicaoResumo {
  fonte: string;
  id: number;
  titulo: string; // "PEC 231/2019"
  ementa: string | null;
}

export interface VotacaoCompleta {
  fonte: string;
  id: string;
  data: string | null;
  orgao: string | null;
  descricao: string;
  aprovada: boolean | null;
  parecer: string | null; // o que exatamente foi votado
  proposicoes: ProposicaoResumo[];
}

export interface ProposicaoDetalhe {
  fonte: string;
  id: number;
  tipo: string;
  numero: number | null;
  ano: number | null;
  ementa: string;
  ementa_detalhada: string | null;
  situacao: string | null;
  tramitacao: string | null;
  orgao: string | null;
  regime: string | null;
  despacho: string | null;
  url_inteiro_teor: string | null;
  keywords: string | null;
}

export interface ArquivoCompra {
  fonte: string;
  titulo: string;
  url: string;
}

export interface TodasEsferasOut {
  ano: number;
  uniao: string;
  estados: string;
  capitais: string;
  total: string;
  entes_somados: number;
  meta: Record<string, unknown>;
}

export interface FornecedorOut {
  cnpj: string;
  cadastro: FichaEmpresa | null;
  vinculos: VinculosEmpresa | null;
  sancoes: Sancao[];
  contratos: ContratoFederal[];
  erros: Record<string, string>;
  meta: Record<string, unknown>;
}
