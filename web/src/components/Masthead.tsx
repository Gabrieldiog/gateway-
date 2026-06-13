"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePulso } from "@/lib/pulso";
import { apiGet, caminho } from "@/lib/api";
import type { FontesOut } from "@/lib/types";

const DIAS = ["DOM", "SEG", "TER", "QUA", "QUI", "SEX", "SÁB"];
const MESES = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"];

function edicaoHoje(): string {
  const d = new Date();
  return `${DIAS[d.getDay()]} · ${String(d.getDate()).padStart(2, "0")} ${MESES[d.getMonth()]} ${d.getFullYear()}`;
}

export function Masthead() {
  const pulso = usePulso();
  const [edicao, setEdicao] = useState<string | null>(null);
  const [fontes, setFontes] = useState<number | null>(null);

  // só no cliente, pra não dar mismatch de hidratação com a data
  useEffect(() => {
    setEdicao(edicaoHoje());
    apiGet<FontesOut>(caminho("fontes"))
      .then((f) => setFontes(f.total))
      .catch(() => setFontes(null));
  }, []);

  return (
    <header className="sticky top-0 z-30 border-b border-ink/15 bg-bg/85 backdrop-blur-sm">
      <div className="mx-auto flex w-full max-w-310 items-center gap-4 px-4 py-3 md:px-6">
        <Link href="/" className="group flex items-baseline gap-2">
          <span className="font-display text-2xl font-semibold tracking-[0.14em] text-ink">
            BALCÃO
          </span>
          <span className="hidden font-editorial text-sm italic text-muted sm:inline">
            diário de dados públicos
          </span>
        </Link>

        <div className="ml-auto hidden items-center gap-5 text-[0.7rem] lg:flex">
          <span className="num uppercase tracking-wider text-muted">
            {edicao ?? "carregando edição…"}
          </span>
          <span className="h-3 w-px bg-line" />
          <span className="num uppercase tracking-wider text-muted">
            {fontes != null ? `${fontes} fontes ativas` : "—"}
          </span>
          <span className="h-3 w-px bg-line" />
          <PulsoBadge ms={pulso?.ms ?? null} cache={pulso?.cache ?? null} />
        </div>

        {/* versão compacta no mobile */}
        <div className="ml-auto flex items-center gap-3 text-[0.7rem] lg:hidden">
          <PulsoBadge ms={pulso?.ms ?? null} cache={pulso?.cache ?? null} />
        </div>
      </div>
      <div className="regua-dupla mx-auto w-full max-w-310" />
    </header>
  );
}

function PulsoBadge({ ms, cache }: { ms: number | null; cache: string | null }) {
  if (ms == null) {
    return <span className="num uppercase tracking-wider text-muted">aguardando consulta</span>;
  }
  const cor =
    cache === "hit" ? "text-ok" : cache === "stale" ? "text-ocre" : "text-accent-2";
  const rotulo = cache ? cache.toUpperCase() : "DIRETO";
  return (
    <span className="num flex items-center gap-1.5 uppercase tracking-wider">
      <span className={`inline-block h-1.5 w-1.5 rounded-full ${cor.replace("text-", "bg-")}`} />
      <span className="text-ink">{ms}ms</span>
      <span className={cor}>{rotulo}</span>
    </span>
  );
}
