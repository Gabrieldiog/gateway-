// A cadência de atualização de cada caderno, de quanto em quanto tempo a
// FONTE oficial publica dado novo (e o Balcão busca). Cada linha foi apurada
// no connector + no calendário real do órgão; é o selo-dateline que o
// CadernoHeader estampa na página.
//
// Ficam de fora, de propósito, quem já tem um selo melhor no lugar:
// - pulso e energia trazem o selo "ao vivo" com o relógio correndo;
// - combustíveis, queimadas, títulos, cidade e agro trazem um selo próprio,
//   contextual, que cita a janela/data exata do dado (mais rico que o rótulo).

export interface Frescor {
  rotulo: string; // 1-3 palavras: a periodicidade
  detalhe: string; // uma linha humana: quando vem o dado novo
}

// chave = href do caderno (o mesmo do sumário)
const FRESCOR: Record<string, Frescor> = {
  "/camara": {
    rotulo: "diário",
    detalhe: "gastos e discursos entram nos dias de sessão; a lista de deputados só muda quando alguém assume ou sai",
  },
  "/senado": {
    rotulo: "irregular",
    detalhe: "o plantel de 81 senadores só muda em eleição ou quando um suplente assume",
  },
  "/votos": {
    rotulo: "dias de sessão",
    detalhe: "voto novo quando o plenário faz votação nominal, em geral de terça a quinta",
  },
  "/dinheiro": {
    rotulo: "mensal",
    detalhe: "a CGU publica por folha mensal; o Bolsa Família sai com uns 2 meses de atraso",
  },
  "/pauta": {
    rotulo: "dias de sessão",
    detalhe: "votações e tramitação entram conforme o plenário trabalha; quase nada no recesso",
  },
  "/compras": {
    rotulo: "diário",
    detalhe: "o PNCP recebe milhares de licitações e contratos todo dia útil",
  },
  "/fornecedor": {
    rotulo: "irregular",
    detalhe: "muda quando a empresa altera algo na Receita (~mensal) ou entra numa lista da CGU (quase diário)",
  },
  "/diarios": {
    rotulo: "dias úteis",
    detalhe: "cada prefeitura publica nos dias úteis; o Querido Diário coleta os novos todo dia",
  },
  "/custo-de-vida": {
    rotulo: "diário a mensal",
    detalhe: "dólar e CDI todo dia útil; a inflação uma vez por mês; o Focus toda segunda",
  },
  "/tesouro": {
    rotulo: "anual",
    detalhe: "as contas de cada ente fecham uma vez por ano, só no exercício seguinte",
  },
  "/arrecadometro": {
    rotulo: "anual",
    detalhe: "o total oficial vem do balanço anual do SICONFI; o contador é projeção, não medição ao vivo",
  },
  "/trabalho": {
    rotulo: "mensal",
    detalhe: "a PNAD Contínua sai todo mês, uns 45 dias depois de fechar o trimestre móvel",
  },
  "/comercio": {
    rotulo: "mensal",
    detalhe: "o MDIC fecha o mês anterior e publica nos primeiros dias do seguinte",
  },
  "/consumidor": {
    rotulo: "trimestral",
    detalhe: "o Banco Central fecha o ranking de reclamações a cada trimestre",
  },
  "/bacen": {
    rotulo: "dias úteis",
    detalhe: "Selic, CDI e câmbio ganham um ponto novo a cada dia útil; IPCA e IGP-M, mensal",
  },
  "/ipeadata": {
    rotulo: "varia por série",
    detalhe: "cada série tem sua periodicidade, câmbio quase diário, PIB trimestral; a maioria é mensal",
  },
  "/ibge": {
    rotulo: "quase estático",
    detalhe: "a divisão de 27 UFs e ~5.570 municípios quase nunca muda",
  },
  "/agua": {
    rotulo: "diário",
    detalhe: "os grandes reservatórios renovam a medição todo dia; açude pequeno pode demorar",
  },
  "/desmatamento": {
    rotulo: "quase diário",
    detalhe: "o DETER/INPE solta alertas nos dias úteis; nuvem atrasa a detecção",
  },
  "/mundo": {
    rotulo: "anual",
    detalhe: "o Banco Mundial consolida os indicadores uma vez por ano (alguns com anos de atraso)",
  },
  "/obras": {
    rotulo: "irregular",
    detalhe: "o órgão atualiza a obra sem data fixa; o que já foi pago entra conforme o SIAFI",
  },
  "/dados": {
    rotulo: "varia por conjunto",
    detalhe: "cada conjunto (ANEEL, MME, ANTT) tem seu próprio calendário de publicação",
  },
  "/saude": {
    rotulo: "mensal",
    detalhe: "o CNES fecha uma nova competência a cada mês",
  },
  "/dengue": {
    rotulo: "semanal",
    detalhe: "o InfoDengue publica um boletim por semana; as semanas recentes ainda se ajustam",
  },
  "/seguranca": {
    rotulo: "mensal",
    detalhe: "o Ministério da Justiça republica a base do Sinesp uma vez por mês",
  },
  "/educacao": {
    rotulo: "anual",
    detalhe: "o Censo Escolar sai todo ano; o IDEB, a nota da escola, só a cada dois",
  },
  "/almanaque": {
    rotulo: "quase diário",
    detalhe: "a CAIXA sorteia de segunda a sábado; o nome no Brasil é retrato do Censo 2010",
  },
};

// acha o frescor do caderno pelo pathname atual (mesma regra do sumário)
export function frescorDoPath(path: string): Frescor | null {
  const chave = Object.keys(FRESCOR).find((href) => path === href || path.startsWith(href + "/"));
  return chave ? FRESCOR[chave] : null;
}
