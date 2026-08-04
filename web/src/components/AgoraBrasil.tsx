"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useBalcao } from "@/hooks/useBalcao";
import { caminho } from "@/lib/api";
import type {
  Acao,
  Cotacao,
  GeracaoEnergia,
  IndicadorEconomico,
  NormalizedResponse,
  Queimada,
} from "@/lib/types";

// o coração vivo da capa: uma fita de agência rolando com os números de
// agora e um painel que se atualiza sozinho, câmbio a cada 30s, energia a
// cada 60s, o resto no ritmo de cada fonte.

const PARES = "USD-BRL,EUR-BRL,BTC-BRL";

// data local de ontem em YYYY-MM-DD (o arquivo do INPE é por dia; o de hoje
// só fecha à noite)
function ontemISO(): string {
  const d = new Date();
  d.setDate(d.getDate() - 1);
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const dia = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${m}-${dia}`;
}

const reais = (v: number, casas = 2) =>
  v.toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas });

interface Item {
  rotulo: string;
  valor: string;
  extra?: string;
  tom?: "sobe" | "desce";
  href: string;
  vivo?: boolean;
}

export function AgoraBrasil() {
  const cot = useBalcao<NormalizedResponse<Cotacao>>(caminho(`cotacoes/last/${PARES}`));
  const bolsa = useBalcao<NormalizedResponse<Acao>>(caminho("b3/acoes/ibov"));
  const infl = useBalcao<NormalizedResponse<IndicadorEconomico>>(caminho("bacen/inflacao"));
  const energia = useBalcao<NormalizedResponse<GeracaoEnergia>>(caminho("ons/geracao"));
  const fogo = useBalcao<NormalizedResponse<Queimada>>(
    caminho("inpe/queimadas", { por: "estado", data: ontemISO(), limit: 1 }),
  );

  const recarregaCot = cot.recarregar;
  const recarregaEnergia = energia.recarregar;
  useEffect(() => {
    const a = setInterval(() => recarregaCot(), 30000);
    const b = setInterval(() => recarregaEnergia(), 60000);
    return () => {
      clearInterval(a);
      clearInterval(b);
    };
  }, [recarregaCot, recarregaEnergia]);

  const cotacoes = cot.dados?.dados ?? [];
  const indicadores = infl.dados?.dados ?? [];
  const sin =
    (energia.dados?.dados ?? []).find((d) => d.regiao === "SIN") ?? energia.dados?.dados?.[0];
  const ibov = bolsa.dados?.dados?.[0];
  const focos = fogo.dados?.meta?.total_focos as number | undefined;

  const itens: Item[] = [];
  for (const c of cotacoes) {
    const nomes: Record<string, string> = { "USD/BRL": "dólar", "EUR/BRL": "euro", "BTC/BRL": "bitcoin" };
    const v = Number(c.compra);
    itens.push({
      rotulo: nomes[c.par] ?? c.par,
      valor: `R$ ${reais(v, v >= 1000 ? 0 : 2)}`,
      extra: c.variacao_pct != null ? `${c.variacao_pct >= 0 ? "▲" : "▼"} ${Math.abs(c.variacao_pct).toFixed(2)}%` : undefined,
      tom: c.variacao_pct != null && c.variacao_pct < 0 ? "desce" : "sobe",
      href: "/pulso",
      vivo: true,
    });
  }
  if (ibov) {
    itens.push({
      rotulo: "ibovespa",
      valor: `${Number(ibov.preco).toLocaleString("pt-BR", { maximumFractionDigits: 0 })} pts`,
      extra: ibov.variacao_pct != null ? `${ibov.variacao_pct >= 0 ? "▲" : "▼"} ${Math.abs(ibov.variacao_pct).toFixed(2)}%` : undefined,
      tom: ibov.variacao_pct != null && ibov.variacao_pct < 0 ? "desce" : "sobe",
      href: "/pulso",
    });
  }
  const selic = indicadores.find((i) => i.chave === "selic");
  if (selic) {
    itens.push({ rotulo: "selic", valor: `${reais(Number(selic.valor))}% a.a.`, href: "/custo-de-vida" });
  }
  const ipca = indicadores.find((i) => i.chave === "ipca12m");
  if (ipca) {
    itens.push({ rotulo: "inflação 12m", valor: `${reais(Number(ipca.valor))}%`, href: "/custo-de-vida" });
  }
  if (sin) {
    itens.push({
      rotulo: "energia agora",
      valor: `${reais(sin.geracao_total / 1000, 1)} GW`,
      extra: `${Math.round((100 * (sin.hidraulica + sin.eolica + sin.solar)) / (sin.geracao_total || 1))}% renovável`,
      href: "/energia",
      vivo: true,
    });
  }
  if (focos != null) {
    itens.push({
      rotulo: "focos de queimada ontem",
      valor: focos.toLocaleString("pt-BR"),
      href: "/queimadas",
    });
  }

  if (!itens.length) return null;

  // a fita leva tudo; o painel escolhe um de cada assunto
  const DESTAQUES = ["dólar", "ibovespa", "selic", "inflação 12m", "energia agora", "focos de queimada ontem"];
  const painel = DESTAQUES.map((r) => itens.find((it) => it.rotulo === r)).filter(
    (it): it is Item => Boolean(it),
  );

  return (
    <section aria-label="números de agora">
      {/* a fita: dois carretéis idênticos emendam o loop */}
      <div className="fita-pausa regua-dupla overflow-hidden border-b border-ink/80 py-2">
        <div className="fita-rola flex w-max items-center">
          {[0, 1].map((volta) => (
            <div key={volta} className="flex items-center" aria-hidden={volta === 1}>
              <span className="num mx-4 flex items-center gap-1.5 text-[0.65rem] font-bold uppercase tracking-[0.2em] text-accent">
                <span className="relative flex h-1.5 w-1.5">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent opacity-70" />
                  <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-accent" />
                </span>
                agora
              </span>
              {itens.map((it) => (
                <span key={`${volta}-${it.rotulo}`} className="mx-4 flex items-baseline gap-2 whitespace-nowrap">
                  <span className="kicker">{it.rotulo}</span>
                  <span key={it.valor} className="imprime num text-sm font-semibold text-ink">
                    {it.valor}
                  </span>
                  {it.extra && (
                    <span className={`num text-xs ${it.tom === "desce" ? "text-rose-600" : "text-emerald-600"}`}>
                      {it.extra}
                    </span>
                  )}
                </span>
              ))}
            </div>
          ))}
        </div>
      </div>

      {/* o painel: os mesmos números, grandes e clicáveis */}
      <div className="mt-6">
        <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
          <p className="kicker">O Brasil, agora</p>
          <p className="num text-[0.68rem] uppercase tracking-wider text-muted">
            se atualiza sozinho · câmbio a cada 30s · energia a cada 60s
          </p>
        </div>
        <div className="grid grid-cols-1 gap-px overflow-hidden rounded-lg border border-line bg-line sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6">
          {painel.map((it, i) => (
            <Link
              key={it.rotulo}
              href={it.href}
              className="imprime group flex flex-col bg-surface p-4 transition-colors hover:bg-surface-2"
              style={{ animationDelay: `${i * 70}ms` }}
            >
              <span className="kicker mb-1.5 flex items-center gap-1.5">
                {it.vivo && (
                  <span className="relative flex h-1.5 w-1.5">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-500 opacity-70" />
                    <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-500" />
                  </span>
                )}
                {it.rotulo}
              </span>
              <span key={it.valor} className="imprime num font-display text-2xl font-semibold leading-none tracking-tight text-ink group-hover:text-accent">
                {it.valor}
              </span>
              {it.extra && (
                <span className={`num mt-1.5 text-xs ${it.tom === "desce" ? "text-rose-600" : it.tom === "sobe" ? "text-emerald-600" : "text-muted"}`}>
                  {it.extra}
                </span>
              )}
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}
