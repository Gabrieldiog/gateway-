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
    ],
  },
  {
    nome: "Economia",
    cadernos: [
      { num: "XII", nome: "Pulso", sub: "câmbio ao vivo", href: "/pulso" },
      { num: "VI", nome: "Impostos", sub: "arrecadação · país, estados, cidades", href: "/tesouro" },
      { num: "IV", nome: "Banco Central", sub: "séries econômicas", href: "/bacen" },
      { num: "X", nome: "IPEADATA", sub: "séries da economia", href: "/ipeadata" },
    ],
  },
  {
    nome: "Território",
    cadernos: [
      { num: "V", nome: "IBGE", sub: "estados e municípios", href: "/ibge" },
    ],
  },
  {
    nome: "Infraestrutura",
    cadernos: [
      { num: "XI", nome: "Dados Abertos", sub: "energia, transporte (CKAN)", href: "/dados" },
    ],
  },
  {
    nome: "Social",
    cadernos: [
      { num: "VII", nome: "Saúde", sub: "estabelecimentos do SUS", href: "/saude" },
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
