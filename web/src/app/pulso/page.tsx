"use client";

import { useEffect, useRef, useState } from "react";
import { CadernoHeader } from "@/components/Caderno";
import { Card } from "@/components/Card";
import { Esqueleto, ErroBox } from "@/components/Estados";
import { useBalcao } from "@/hooks/useBalcao";
import { useTicker } from "@/hooks/useTicker";
import { caminho } from "@/lib/api";
import type { Acao, Cotacao, NormalizedResponse } from "@/lib/types";

const PARES = "USD-BRL,EUR-BRL,GBP-BRL,XAU-BRL,BTC-BRL,ETH-BRL,SOL-BRL";
const INTERVALO = 20000; // 20s

// o telão em seções: moedas, ouro e cripto (a ordem dentro de cada uma importa)
const GRUPOS: { titulo: string; nota?: string; pares: string[] }[] = [
  { titulo: "Moedas", pares: ["USD/BRL", "EUR/BRL", "GBP/BRL"] },
  { titulo: "Ouro", nota: "cotação da onça troy (31,1 g)", pares: ["XAU/BRL"] },
  { titulo: "Cripto", pares: ["BTC/BRL", "ETH/BRL", "SOL/BRL"] },
];

// rótulo amigável quando a sigla do par não se explica sozinha
const APELIDOS: Record<string, string> = { "XAU/BRL": "OURO" };

// a bolsa vem por outra fonte (b3), com ~15 min de atraso no plano gratuito
const TICKERS_B3 = "ibov,PETR4,VALE3,ITUB4";

function formataPreco(v: number): string {
  if (v >= 1000) return v.toLocaleString("pt-BR", { maximumFractionDigits: 0 });
  return v.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 4 });
}

function horaDe(ts: string | null): string {
  const m = ts?.match(/\d{2}:\d{2}:\d{2}/);
  return m ? m[0] : "—";
}

function TickerCotacao({ c }: { c: Cotacao }) {
  const alvo = Number(c.compra);
  const valor = useTicker(alvo);
  const anterior = useRef(alvo);
  const [dir, setDir] = useState<"sobe" | "desce" | null>(null);

  // quando o valor muda entre dois polls, pisca verde (subiu) ou vermelho (caiu)
  useEffect(() => {
    if (alvo > anterior.current) setDir("sobe");
    else if (alvo < anterior.current) setDir("desce");
    anterior.current = alvo;
    const id = setTimeout(() => setDir(null), 1000);
    return () => clearTimeout(id);
  }, [alvo]);

  const variacao = c.variacao_pct ?? 0;
  const positiva = variacao >= 0;
  const corValor =
    dir === "sobe" ? "text-emerald-500" : dir === "desce" ? "text-rose-500" : "text-ink";

  return (
    <Card className="p-5">
      <div className="flex items-baseline justify-between">
        <span className="num text-sm font-semibold uppercase tracking-wider text-ink">
          {APELIDOS[c.par] ?? c.par}
        </span>
        <span className={`num text-xs ${positiva ? "text-emerald-500" : "text-rose-500"}`}>
          {positiva ? "▲" : "▼"} {Math.abs(variacao).toFixed(2)}%
        </span>
      </div>
      <p
        className={`num mt-2 font-display text-4xl font-semibold tracking-tight transition-colors duration-500 ${corValor}`}
      >
        R$ {formataPreco(valor)}
      </p>
      <p className="mt-1.5 truncate text-xs text-muted" title={c.nome ?? ""}>
        {c.nome} · {horaDe(c.atualizado)}
      </p>
    </Card>
  );
}

function CardAcao({ a }: { a: Acao }) {
  const indice = a.moeda == null;
  const preco = Number(a.preco);
  const variacao = a.variacao_pct ?? 0;
  const positiva = variacao >= 0;
  return (
    <Card className="p-5">
      <div className="flex items-baseline justify-between">
        <span className="num text-sm font-semibold uppercase tracking-wider text-ink">{a.ticker}</span>
        <span className={`num text-xs ${positiva ? "text-emerald-500" : "text-rose-500"}`}>
          {positiva ? "▲" : "▼"} {Math.abs(variacao).toFixed(2)}%
        </span>
      </div>
      <p className="num mt-2 font-display text-4xl font-semibold tracking-tight text-ink">
        {indice
          ? preco.toLocaleString("pt-BR", { maximumFractionDigits: 0 })
          : `R$ ${preco.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
        {indice && <span className="ml-1.5 align-baseline text-base text-muted">pts</span>}
      </p>
      <p className="mt-1.5 truncate text-xs text-muted" title={a.nome ?? ""}>
        {a.nome}
      </p>
    </Card>
  );
}

export default function CadernoPulso() {
  const cot = useBalcao<NormalizedResponse<Cotacao>>(caminho(`cotacoes/last/${PARES}`));
  const bolsa = useBalcao<NormalizedResponse<Acao>>(caminho(`b3/acoes/${TICKERS_B3}`));
  const cotacoes = cot.dados?.dados ?? [];
  const acoes = bolsa.dados?.dados ?? [];
  const { recarregar } = cot;
  const recarregarBolsa = bolsa.recarregar;

  // polling: refaz a cada 20s pra o número mudar sozinho quando o mercado mexe.
  // a bolsa entra no mesmo ciclo — o cache do gateway segura o upstream
  useEffect(() => {
    const id = setInterval(() => {
      recarregar();
      recarregarBolsa();
    }, INTERVALO);
    return () => clearInterval(id);
  }, [recarregar, recarregarBolsa]);

  return (
    <div>
      <CadernoHeader
        numero="XII"
        kicker="AwesomeAPI · mercado"
        titulo="Pulso do Brasil"
        resumo="Câmbio, ouro e cripto quase em tempo real, pelo preço de mercado. A página se atualiza sozinha a cada 20 segundos — quando o mercado mexe, o número desliza pro novo valor. Dado vivo, não a foto de ontem."
      />

      <div className="mb-5 flex items-center gap-2">
        <span className="relative flex h-2.5 w-2.5">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent opacity-75" />
          <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-accent" />
        </span>
        <span className="num text-xs uppercase tracking-wider text-muted">ao vivo · atualiza a cada 20s</span>
      </div>

      {cot.erro ? (
        <ErroBox erro={cot.erro} aoTentar={recarregar} />
      ) : !cotacoes.length ? (
        <Esqueleto linhas={4} />
      ) : (
        <div className="flex flex-col gap-7">
          {GRUPOS.map((g) => {
            const doGrupo = g.pares
              .map((par) => cotacoes.find((c) => c.par === par))
              .filter((c): c is Cotacao => Boolean(c));
            if (!doGrupo.length) return null;
            return (
              <section key={g.titulo}>
                <p className="kicker mb-3">
                  {g.titulo}
                  {g.nota && <span className="ml-2 normal-case tracking-normal text-muted">· {g.nota}</span>}
                </p>
                <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
                  {doGrupo.map((c) => (
                    <TickerCotacao key={c.par} c={c} />
                  ))}
                </div>
              </section>
            );
          })}

          {acoes.length > 0 && (
            <section>
              <p className="kicker mb-3">
                Bolsa
                <span className="ml-2 normal-case tracking-normal text-muted">
                  · B3, com ~15 min de atraso
                </span>
              </p>
              <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
                {acoes.map((a) => (
                  <CardAcao key={a.ticker} a={a} />
                ))}
              </div>
            </section>
          )}
        </div>
      )}

      <p className="mt-7 border-t border-line pt-3 font-editorial text-sm italic text-muted">
        Cotações de mercado via AwesomeAPI (preço de referência, não o câmbio oficial). O dólar
        oficial do Banco Central (PTAX) fica no caderno do Banco Central — ele muda só algumas vezes
        ao dia.
      </p>
    </div>
  );
}
