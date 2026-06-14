export interface Caderno {
  num: string;
  nome: string;
  sub: string;
  href: string;
}

export const CADERNOS: Caderno[] = [
  { num: "I", nome: "Capa", sub: "busca unificada", href: "/" },
  { num: "II", nome: "Câmara", sub: "deputados e gastos", href: "/camara" },
  { num: "III", nome: "Senado", sub: "senadores", href: "/senado" },
  { num: "IV", nome: "Banco Central", sub: "séries econômicas", href: "/bacen" },
  { num: "V", nome: "IBGE", sub: "estados e municípios", href: "/ibge" },
  { num: "VI", nome: "Manual", sub: "como chamar a API", href: "/docs" },
  { num: "VII", nome: "Expediente", sub: "as fontes", href: "/fontes" },
];

export function cadernoAtivo(path: string, href: string): boolean {
  return href === "/" ? path === "/" : path.startsWith(href);
}
