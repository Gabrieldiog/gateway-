// datas dinâmicas: nada de ano ou mês cravado no código, as listas de
// filtro seguem o calendário sozinhas, e o "mais recente" é decidido pelo
// gateway (walk-back), não por nós.
export const ANO_ATUAL = new Date().getFullYear();

// intervalo inclusivo; decrescente quando de > ate
export function anos(de: number, ate: number): number[] {
  const passo = de >= ate ? -1 : 1;
  const lista: number[] = [];
  for (let a = de; passo > 0 ? a <= ate : a >= ate; a += passo) lista.push(a);
  return lista;
}

const MES_CURTO = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];

// últimos n meses (mais novo primeiro) no formato AAAAMM da Transparência
export function ultimosMeses(n: number): { valor: string; label: string }[] {
  const lista: { valor: string; label: string }[] = [];
  const d = new Date();
  d.setDate(1);
  for (let i = 0; i < n; i++) {
    lista.push({
      valor: `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, "0")}`,
      label: `${MES_CURTO[d.getMonth()]}/${d.getFullYear()}`,
    });
    d.setMonth(d.getMonth() - 1);
  }
  return lista;
}

export function rotuloMesAAAAMM(m: string | undefined | null): string {
  if (!m || m.length !== 6) return "sem dado";
  return `${MES_CURTO[Number(m.slice(4)) - 1]}/${m.slice(0, 4)}`;
}
