// nome de gente pra cada fonte do gateway — usado nas mensagens de erro
// pro leitor saber QUEM caiu ("o Banco Central"), não um codinome.
export const NOME_FONTE: Record<string, string> = {
  ana: "a ANA (Agência Nacional de Águas)",
  aneel: "a ANEEL",
  anp: "a ANP",
  antt: "a ANTT",
  b3: "a B3 (via brapi)",
  bacen: "o Banco Central",
  brasilapi: "a BrasilAPI (Receita Federal)",
  camara: "a Câmara dos Deputados",
  comex: "o ComexStat (MDIC)",
  cotacoes: "a AwesomeAPI de câmbio",
  conab: "a CONAB",
  datajud: "o DataJud (CNJ)",
  diarios: "o Querido Diário (OKBR)",
  focus: "o Boletim Focus (Banco Central)",
  ibge: "o IBGE",
  infodengue: "o InfoDengue (Fiocruz)",
  inpe: "o INPE",
  ipeadata: "o IPEADATA",
  mme: "o Ministério de Minas e Energia",
  obrasgov: "o Obrasgov (Ministério da Gestão)",
  ons: "o ONS",
  pncp: "o PNCP",
  senado: "o Senado Federal",
  sidra: "o SIDRA (IBGE)",
  sus: "o CNES (Ministério da Saúde)",
  tesouro: "o Tesouro Nacional",
  tesourodireto: "o Tesouro Direto",
  transparencia: "o Portal da Transparência",
  tse: "o TSE",
};

export function nomeDaFonte(codigo: string | undefined): string {
  if (!codigo) return "a fonte oficial";
  return NOME_FONTE[codigo] ?? `a fonte "${codigo}"`;
}
