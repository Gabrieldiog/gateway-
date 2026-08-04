import type { ErroBalcao } from "./types";
import { registraPulso } from "./pulso";

export class BalcaoError extends Error {
  status: number;
  detalhes?: Record<string, unknown>;
  constructor(mensagem: string, status: number, detalhes?: Record<string, unknown>) {
    super(mensagem);
    this.status = status;
    this.detalhes = detalhes;
  }
}

// monta /api/balcao/<recurso>?<query> a partir de params, ignorando vazios
export function caminho(recurso: string, params?: Record<string, string | number | undefined>): string {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params ?? {})) {
    if (v !== undefined && v !== "" && v !== null) qs.set(k, String(v));
  }
  const query = qs.toString();
  return `/api/balcao/${recurso}${query ? `?${query}` : ""}`;
}

export async function apiGet<T>(url: string, signal?: AbortSignal): Promise<T> {
  const t0 = performance.now();
  const resp = await fetch(url, { signal });
  const corpo = await resp.json().catch(() => null);
  const ms = Math.round(performance.now() - t0);
  // registra a latência real (medida no cliente) e o cache que veio no meta
  const cache = (corpo as { meta?: { cache?: string } } | null)?.meta?.cache ?? null;
  registraPulso({ ms, cache, em: t0 });
  if (!resp.ok) {
    const erro = corpo as ErroBalcao | null;
    throw new BalcaoError(erro?.erro ?? `erro ${resp.status}`, resp.status, erro?.detalhes);
  }
  return corpo as T;
}

const brl = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
export function formataBRL(valor: string | number): string {
  const n = typeof valor === "string" ? Number(valor) : valor;
  return Number.isFinite(n) ? brl.format(n) : "sem dado";
}

// escolhe a unidade certa pro valor: a União vem em trilhões, um estado em
// bilhões, uma cidadezinha em milhões. Devolve o número já na escala + a sigla.
export function escalaReais(valor: string | number): { valor: number; unidade: string } {
  const n = typeof valor === "string" ? Number(valor) : valor;
  if (!Number.isFinite(n)) return { valor: 0, unidade: "" };
  const abs = Math.abs(n);
  if (abs >= 1e12) return { valor: n / 1e12, unidade: "tri" };
  if (abs >= 1e9) return { valor: n / 1e9, unidade: "bi" };
  if (abs >= 1e6) return { valor: n / 1e6, unidade: "mi" };
  if (abs >= 1e3) return { valor: n / 1e3, unidade: "mil" };
  return { valor: n, unidade: "" };
}

// reais em escala curta numa string só: "R$ 5,87 tri", "R$ 361 bi", "R$ 8,5 mi"
export function formataReaisCompacto(valor: string | number): string {
  const { valor: v, unidade } = escalaReais(valor);
  if (!unidade) return formataBRL(v);
  return `R$ ${v.toLocaleString("pt-BR", { maximumFractionDigits: v < 100 ? 2 : 0 })} ${unidade}`;
}

export function formataData(iso: string | null): string {
  if (!iso) return "sem dado";
  const [a, m, d] = iso.split("-");
  return d ? `${d}/${m}/${a}` : iso;
}
