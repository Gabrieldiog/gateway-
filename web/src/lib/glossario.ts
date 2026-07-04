// o dicionário do jornal: jargão explicado em uma frase, no tom da casa.
// O componente <Termo t="..."> sublinha a palavra e abre a explicação.
export interface Verbete {
  titulo: string;
  texto: string;
}

export const GLOSSARIO: Record<string, Verbete> = {
  focos: {
    titulo: "Foco de calor",
    texto:
      "Um pixel quente visto pelo satélite do INPE — um ponto onde o sensor detectou temperatura de queima. Não é “um incêndio”: um incêndio grande vira dezenas de focos, e uma queimada pequena pode passar entre duas passagens do satélite.",
  },
  empenhado: {
    titulo: "Empenhado",
    texto:
      "A primeira etapa do gasto público: o governo reserva o dinheiro e se compromete com a despesa. Ainda não saiu do caixa — o caminho é empenhar → liquidar → pagar.",
  },
  pago: {
    titulo: "Pago",
    texto:
      "A última etapa do gasto: o dinheiro saiu do caixa do governo e chegou a quem devia receber. A diferença entre o empenhado e o pago mostra o que ficou prometido mas ainda não foi.",
  },
  fob: {
    titulo: "Valor FOB",
    texto:
      "“Free on Board”: o preço da mercadoria posta no navio, no porto de saída — sem frete nem seguro internacionais. É o padrão mundial das estatísticas de comércio exterior.",
  },
  rt: {
    titulo: "Rt — número de reprodução",
    texto:
      "Quantas pessoas, em média, cada doente contamina. Acima de 1, a epidemia cresce; abaixo de 1, encolhe.",
  },
  nowcast: {
    titulo: "Nowcast",
    texto:
      "Estimativa que corrige o atraso da papelada: casos recentes ainda não chegaram todos ao sistema, então o modelo da Fiocruz calcula quantos devem aparecer. Por isso as últimas semanas se ajustam a cada boletim.",
  },
  selic: {
    titulo: "Selic",
    texto:
      "A taxa básica de juros do país, definida pelo Banco Central a cada 45 dias. É a referência de todos os outros juros — do cartão ao financiamento — e do rendimento da renda fixa.",
  },
  cdi: {
    titulo: "CDI",
    texto:
      "A taxa dos empréstimos de um dia que os bancos fazem entre si, sempre colada na Selic. É o termômetro dos investimentos de renda fixa — o famoso “% do CDI”.",
  },
  ipca: {
    titulo: "IPCA",
    texto:
      "O índice oficial de inflação do Brasil, medido pelo IBGE: quanto subiu o custo de vida das famílias que ganham até 40 salários mínimos.",
  },
  ipca12m: {
    titulo: "IPCA acumulado em 12 meses",
    texto:
      "A inflação oficial somada dos últimos 12 meses — o número que resume quanto o seu dinheiro perdeu de valor em um ano.",
  },
  inpc: {
    titulo: "INPC",
    texto:
      "Inflação medida pelo IBGE focada nas famílias de renda mais baixa (até 5 salários mínimos). É o índice que costuma reajustar salário mínimo e aposentadorias.",
  },
  igpm: {
    titulo: "IGP-M",
    texto:
      "O “índice do aluguel”: inflação calculada pela FGV, muito usada em contratos de aluguel e tarifas. Sobe e desce com mais força que o IPCA porque pesa o atacado e o dólar.",
  },
  poupanca: {
    titulo: "Poupança",
    texto:
      "O rendimento mensal da caderneta: 0,5% ao mês + TR quando a Selic passa de 8,5% ao ano; 70% da Selic quando está abaixo.",
  },
  ceap: {
    titulo: "Cota parlamentar (CEAP)",
    texto:
      "Verba mensal que cada deputado pode gastar no exercício do mandato — passagens, combustível, escritório, divulgação. O deputado comprova a despesa e a Câmara ressarce.",
  },
  ceis: {
    titulo: "CEIS",
    texto:
      "Cadastro de Empresas Inidôneas e Suspensas: a lista de quem está proibido de fechar contrato com o poder público.",
  },
  cnep: {
    titulo: "CNEP",
    texto:
      "Cadastro Nacional de Empresas Punidas: as punições aplicadas pela Lei Anticorrupção — multas e proibições por corrupção comprovada.",
  },
  sin: {
    titulo: "SIN — Sistema Interligado Nacional",
    texto:
      "A grande rede elétrica que conecta usinas e consumidores de quase todo o Brasil. O número que você vê é a soma do que essa rede está gerando neste instante.",
  },
  pregao: {
    titulo: "Pregão eletrônico",
    texto:
      "A modalidade mais comum de licitação: um leilão reverso pela internet — vence quem oferece o MENOR preço pelo que o governo quer comprar.",
  },
  dispensa: {
    titulo: "Dispensa de licitação",
    texto:
      "Compra sem concorrência, permitida por lei em situações específicas (valores baixos, emergência). É legal — mas é onde o olho do leitor vale mais.",
  },
  emenda: {
    titulo: "Emenda parlamentar",
    texto:
      "Dinheiro do Orçamento que deputados e senadores direcionam pra obras e projetos, geralmente nos estados que os elegeram.",
  },
  focus: {
    titulo: "Boletim Focus",
    texto:
      "Pesquisa semanal do Banco Central com mais de cem instituições financeiras: a mediana do que o mercado espera pra inflação, juros e dólar. É expectativa, não promessa.",
  },
  deter: {
    titulo: "DETER — alerta de desmatamento",
    texto:
      "O sistema do INPE que vasculha imagens de satélite quase todo dia e acende um alerta onde a floresta sumiu. Serve pra fiscalização chegar rápido — a conta oficial do ano é outra, o PRODES. Nuvem esconde e corte pequeno escapa: o alerta é piso, não teto.",
  },
  corteraso: {
    titulo: "Corte raso",
    texto:
      "O desmatamento completo: a vegetação foi toda ao chão. É a classe mais grave dos alertas — diferente da degradação, onde a floresta ainda está de pé, mas danificada.",
  },
  indicereclamacoes: {
    titulo: "Índice de reclamações",
    texto:
      "Reclamações julgadas PROCEDENTES pelo Banco Central a cada 1 milhão de clientes da instituição. Procedente = o banco realmente descumpriu uma regra. O BC só compara os grandes entre si (Top 15) — banco pequeno com poucos clientes inflaria o índice.",
  },
  volumeutil: {
    titulo: "Volume útil",
    texto:
      "A parte da água do reservatório que dá pra usar de verdade — o que está acima da tomada d'água. 100% é reservatório cheio; 0% não é seco, é o ponto abaixo do qual a água não desce mais por gravidade.",
  },
  afluencia: {
    titulo: "Afluência",
    texto:
      "Quanta água está CHEGANDO ao reservatório, em metros cúbicos por segundo — os rios e a chuva que desaguam nele. Afluência maior que a defluência = reservatório enchendo.",
  },
  defluencia: {
    titulo: "Defluência",
    texto:
      "Quanta água está SAINDO do reservatório, em metros cúbicos por segundo — pelas turbinas, pelo vertedouro ou pro abastecimento. Defluência maior que a afluência = reservatório baixando.",
  },
  cota: {
    titulo: "Cota",
    texto:
      "O nível da água, em metros em relação ao nível do mar. É a régua do reservatório: cota subindo é água entrando. Cada reservatório tem sua faixa própria — compare a cota com ela mesma ao longo dos dias, não entre reservatórios.",
  },
};
