// nome de gente pra cada fonte do gateway — usado nas mensagens de erro
// pro leitor saber QUEM caiu ("o Banco Central"), não um codinome.
export const NOME_FONTE: Record<string, string> = {
  aneel: "a ANEEL",
  anp: "a ANP",
  antt: "a ANTT",
  b3: "a B3 (via brapi)",
  bacen: "o Banco Central",
  camara: "a Câmara dos Deputados",
  comex: "o ComexStat (MDIC)",
  cotacoes: "a AwesomeAPI de câmbio",
  datajud: "o DataJud (CNJ)",
  focus: "o Boletim Focus (Banco Central)",
  ibge: "o IBGE",
  infodengue: "o InfoDengue (Fiocruz)",
  inpe: "o INPE",
  ipeadata: "o IPEADATA",
  mme: "o Ministério de Minas e Energia",
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
