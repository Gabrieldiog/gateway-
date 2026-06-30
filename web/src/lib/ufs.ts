export const UFS = [
  "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS",
  "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC",
  "SE", "SP", "TO",
];

// código IBGE da capital de cada UF — default sensato no modo cidade, pra
// já mostrar algo sem o usuário precisar escolher.
export const CAPITAIS: Record<string, string> = {
  AC: "1200401", AL: "2704302", AM: "1302603", AP: "1600303", BA: "2927408",
  CE: "2304400", DF: "5300108", ES: "3205309", GO: "5208707", MA: "2111300",
  MG: "3106200", MS: "5002704", MT: "5103403", PA: "1501402", PB: "2507507",
  PE: "2611606", PI: "2211001", PR: "4106902", RJ: "3304557", RN: "2408102",
  RO: "1100205", RR: "1400100", RS: "4314902", SC: "4205407", SE: "2800308",
  SP: "3550308", TO: "1721000",
};
