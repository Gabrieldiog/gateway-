"use client";

import { useEffect, useRef, useState } from "react";
import { CadernoHeader } from "@/components/Caderno";
import { Card } from "@/components/Card";
import { Esqueleto, ErroBox } from "@/components/Estados";
import { useBalcao } from "@/hooks/useBalcao";
import { useTicker } from "@/hooks/useTicker";
import { caminho } from "@/lib/api";
import type { Cotacao, NormalizedResponse } from "@/lib/types";

const PARES = "USD-BRL,EUR-BRL,GBP-BRL,BTC-BRL";
const INTERVALO = 20000; // 20s

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
        <span className="num text-sm font-semibold uppercase tracking-wider text-ink">{c.par}</span>
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

export default function CadernoPulso() {
  const cot = useBalcao<NormalizedResponse<Cotacao>>(caminho(`cotacoes/last/${PARES}`));
  const cotacoes = cot.dados?.dados ?? [];
  const { recarregar } = cot;

  // polling: refaz a cada 20s pra o número mudar sozinho quando o mercado mexe
  useEffect(() => {
    const id = setInterval(() => recarregar(), INTERVALO);
    return () => clearInterval(id);
  }, [recarregar]);

  return (
    <div>
      <CadernoHeader
        numero="XII"
        kicker="AwesomeAPI · mercado"
        titulo="Pulso do Brasil"
        resumo="Câmbio e cripto quase em tempo real, pelo preço de mercado. A página se atualiza sozinha a cada 20 segundos — quando o mercado mexe, o número desliza pro novo valor. Dado vivo, não a foto de ontem."
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
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {cotacoes.map((c) => (
            <TickerCotacao key={c.par} c={c} />
          ))}
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
