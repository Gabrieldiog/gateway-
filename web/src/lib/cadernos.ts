export interface Caderno {
  num: string;
  nome: string;
  sub: string;
  href: string;
}

export interface Grupo {
  nome: string;
  cadernos: Caderno[];
}

// a Capa fica solta no topo do sumário; o número é a "edição" fixa de cada
// caderno (por isso pula dentro dos grupos) — o grupo é o tema, não a ordem.
export const CAPA: Caderno = { num: "I", nome: "Capa", sub: "busca unificada", href: "/" };

export const GRUPOS: Grupo[] = [
  {
    nome: "Governo",
    cadernos: [
      { num: "II", nome: "Câmara", sub: "deputados e gastos", href: "/camara" },
      { num: "III", nome: "Senado", sub: "senadores", href: "/senado" },
      { num: "VIII", nome: "Votos", sub: "como cada deputado votou", href: "/votos" },
      { num: "XVII", nome: "Dinheiro Público", sub: "emendas, sanções e Bolsa Família", href: "/dinheiro" },
      { num: "XVIII", nome: "Em Pauta", sub: "o que a Câmara votou e movimentou", href: "/pauta" },
    ],
  },
  {
    nome: "Economia",
    cadernos: [
      { num: "XII", nome: "Pulso", sub: "câmbio, ouro e cripto ao vivo", href: "/pulso" },
      { num: "XIV", nome: "Custo de Vida", sub: "inflação e o que o mercado espera", href: "/custo-de-vida" },
      { num: "VI", nome: "Impostos", sub: "arrecadação · país, estados, cidades", href: "/tesouro" },
      { num: "XIII", nome: "Arrecadômetro", sub: "quanto o Brasil já arrecadou", href: "/arrecadometro" },
      { num: "XX", nome: "Comércio Exterior", sub: "balança comercial e parceiros", href: "/comercio" },
      { num: "IV", nome: "Banco Central", sub: "séries econômicas", href: "/bacen" },
      { num: "X", nome: "IPEADATA", sub: "séries da economia", href: "/ipeadata" },
    ],
  },
  {
    nome: "Território",
    cadernos: [
      { num: "V", nome: "IBGE", sub: "estados e municípios", href: "/ibge" },
      { num: "XVI", nome: "Queimadas", sub: "focos de incêndio por estado e bioma", href: "/queimadas" },
    ],
  },
  {
    nome: "Infraestrutura",
    cadernos: [
      { num: "XV", nome: "Energia", sub: "geração do país ao vivo", href: "/energia" },
      { num: "XI", nome: "Dados Abertos", sub: "energia, transporte (CKAN)", href: "/dados" },
    ],
  },
  {
    nome: "Social",
    cadernos: [
      { num: "VII", nome: "Saúde", sub: "estabelecimentos do SUS", href: "/saude" },
      { num: "XIX", nome: "Dengue", sub: "alerta por cidade, semana a semana", href: "/dengue" },
      { num: "IX", nome: "Agro", sub: "produção e rebanho", href: "/agro" },
    ],
  },
  {
    nome: "Sobre",
    cadernos: [
      { num: "XII", nome: "Manual", sub: "como chamar a API", href: "/docs" },
      { num: "XIII", nome: "Expediente", sub: "as fontes", href: "/fontes" },
    ],
  },
];

// lista plana na ordem do sumário — pro índice mobile e contagens
export const CADERNOS: Caderno[] = [CAPA, ...GRUPOS.flatMap((g) => g.cadernos)];

export function cadernoAtivo(path: string, href: string): boolean {
  return href === "/" ? path === "/" : path.startsWith(href);
}
