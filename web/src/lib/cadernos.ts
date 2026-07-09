export interface Caderno {
  num: string;
  nome: string;
  sub: string;
  href: string;
}

export interface Grupo {
  nome: string;
  desc?: string;
  cadernos: Caderno[];
}

// a Capa fica solta no topo do sumário; o número é a "edição" fixa de cada
// caderno (por isso pula dentro dos grupos) — o grupo é o tema, não a ordem.
export const CAPA: Caderno = { num: "I", nome: "Capa", sub: "busca unificada", href: "/" };

export const GRUPOS: Grupo[] = [
  {
    nome: "Governo",
    desc: "Quem manda e quanto custa: deputados, senadores, cada voto nominal, emendas, sanções e as compras públicas.",
    cadernos: [
      { num: "II", nome: "Câmara", sub: "deputados e gastos", href: "/camara" },
      { num: "III", nome: "Senado", sub: "senadores", href: "/senado" },
      { num: "VIII", nome: "Votos", sub: "como cada deputado votou", href: "/votos" },
      { num: "XVII", nome: "Dinheiro Público", sub: "emendas, sanções e Bolsa Família", href: "/dinheiro" },
      { num: "XVIII", nome: "Em Pauta", sub: "o que a Câmara votou e movimentou", href: "/pauta" },
      { num: "XXIII", nome: "Compras Públicas", sub: "licitações e contratos (PNCP)", href: "/compras" },
      { num: "XXVII", nome: "Ficha do Fornecedor", sub: "um CNPJ, quatro fontes", href: "/fornecedor" },
      { num: "XXIX", nome: "Diários Oficiais", sub: "busque no papel da prefeitura", href: "/diarios" },
    ],
  },
  {
    nome: "Economia",
    desc: "O dinheiro do país e o do seu bolso: câmbio ao vivo, inflação, impostos, comércio exterior, combustíveis e o Tesouro.",
    cadernos: [
      { num: "XII", nome: "Pulso", sub: "câmbio, ouro e cripto ao vivo", href: "/pulso" },
      { num: "XIV", nome: "Custo de Vida", sub: "inflação e o que o mercado espera", href: "/custo-de-vida" },
      { num: "VI", nome: "Impostos", sub: "arrecadação · país, estados, cidades", href: "/tesouro" },
      { num: "XIII", nome: "Arrecadômetro", sub: "quanto o Brasil já arrecadou", href: "/arrecadometro" },
      { num: "XXXVII", nome: "Trabalho e Renda", sub: "desemprego e salário pela PNAD", href: "/trabalho" },
      { num: "XX", nome: "Comércio Exterior", sub: "balança comercial e parceiros", href: "/comercio" },
      { num: "XXI", nome: "Combustíveis", sub: "gasolina, etanol e gás por estado", href: "/combustiveis" },
      { num: "XXII", nome: "Títulos Públicos", sub: "Tesouro Direto: taxa e preço do dia", href: "/titulos" },
      { num: "XXXII", nome: "Consumidor", sub: "os bancos que mais geram reclamação", href: "/consumidor" },
      { num: "IV", nome: "Banco Central", sub: "séries econômicas", href: "/bacen" },
      { num: "X", nome: "IPEADATA", sub: "séries da economia", href: "/ipeadata" },
    ],
  },
  {
    nome: "Território",
    desc: "O mapa do Brasil: estados, municípios, as queimadas que os satélites enxergam e a água dos reservatórios.",
    cadernos: [
      { num: "XXVIII", nome: "Minha Cidade", sub: "censo, PIB e as contas da prefeitura", href: "/cidade" },
      { num: "V", nome: "IBGE", sub: "estados e municípios", href: "/ibge" },
      { num: "XVI", nome: "Queimadas", sub: "focos de incêndio por estado e bioma", href: "/queimadas" },
      { num: "XXXI", nome: "Água", sub: "quanto têm os reservatórios, dia a dia", href: "/agua" },
      { num: "XXXV", nome: "Desmatamento", sub: "os alertas de satélite do último mês", href: "/desmatamento" },
      { num: "XXXIV", nome: "Brasil no Mundo", sub: "o país comparado com o planeta", href: "/mundo" },
    ],
  },
  {
    nome: "Infraestrutura",
    desc: "A máquina funcionando: a geração de energia do país em tempo real e os dados abertos de transporte.",
    cadernos: [
      { num: "XV", nome: "Energia", sub: "geração do país ao vivo", href: "/energia" },
      { num: "XXX", nome: "Obras Públicas", sub: "as federais — inclusive as paradas", href: "/obras" },
      { num: "XI", nome: "Dados Abertos", sub: "energia, transporte (CKAN)", href: "/dados" },
    ],
  },
  {
    nome: "Social",
    desc: "O dia a dia de quem vive aqui: os estabelecimentos do SUS, o alerta de dengue da sua cidade e o agro que alimenta.",
    cadernos: [
      { num: "VII", nome: "Saúde", sub: "estabelecimentos do SUS", href: "/saude" },
      { num: "XIX", nome: "Dengue", sub: "alerta por cidade, semana a semana", href: "/dengue" },
      { num: "XXXVIII", nome: "Segurança", sub: "as ocorrências criminais por estado", href: "/seguranca" },
      { num: "IX", nome: "Agro", sub: "safra de agora, preços e rebanho", href: "/agro" },
      { num: "XXXVI", nome: "Educação", sub: "o IDEB e as escolas da sua cidade", href: "/educacao" },
      { num: "XXXIII", nome: "Almanaque", sub: "a Mega de ontem e o seu nome no Brasil", href: "/almanaque" },
    ],
  },
  {
    nome: "Sobre",
    cadernos: [
      { num: "XXIV", nome: "Sobre o Balcão", sub: "o que é este jornal", href: "/sobre" },
      { num: "XXVI", nome: "Expediente", sub: "as fontes oficiais", href: "/fontes" },
    ],
  },
  {
    nome: "Desenvolvedores",
    cadernos: [
      { num: "XXV", nome: "Manual da API", sub: "como chamar cada fonte", href: "/docs" },
      { num: "XL", nome: "Índice de Endpoints", sub: "todas as chamadas, por tema", href: "/endpoints" },
      { num: "XXXIX", nome: "Termos de Uso", sub: "a licença, os limites e as fontes", href: "/termos" },
    ],
  },
];

// os grupos de leitura — a vitrine da capa não mostra as seções institucionais
export const TEMAS: Grupo[] = GRUPOS.filter(
  (g) => g.nome !== "Sobre" && g.nome !== "Desenvolvedores",
);

// lista plana na ordem do sumário — pro índice mobile e contagens
export const CADERNOS: Caderno[] = [CAPA, ...GRUPOS.flatMap((g) => g.cadernos)];

export function cadernoAtivo(path: string, href: string): boolean {
  return href === "/" ? path === "/" : path.startsWith(href);
}

// numeração romana por grupo: cada seção recomeça em I, II, III... como um
// jornal de verdade (o número é a posição do caderno DENTRO do seu tema)
const ROMANOS = [
  "", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X",
  "XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII", "XVIII", "XIX", "XX",
];

function romano(n: number): string {
  return ROMANOS[n] ?? String(n);
}

// href -> numeral da posição no grupo (a Capa é a abertura, fica "I")
const NUMERO_POR_HREF: Record<string, string> = { [CAPA.href]: "I" };
for (const g of GRUPOS) {
  g.cadernos.forEach((c, i) => {
    NUMERO_POR_HREF[c.href] = romano(i + 1);
  });
}

export function numeroDoCaderno(href: string): string {
  return NUMERO_POR_HREF[href] ?? "";
}

// pra o cabeçalho de cada página achar seu número pelo pathname atual
export function numeroDoPath(path: string): string {
  if (path === "/") return "I";
  const achado = [CAPA, ...GRUPOS.flatMap((g) => g.cadernos)].find(
    (c) => c.href !== "/" && path.startsWith(c.href),
  );
  return achado ? numeroDoCaderno(achado.href) : "";
}
