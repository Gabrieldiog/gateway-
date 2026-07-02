"use client";

import { useEffect, useState } from "react";

// selos de frescor dos cadernos: etiquetas de impressão em duas células —
// a da esquerda é o carimbo (o que é), a da direita é o papel (o detalhe).
// Nos ao-vivo o relógio anda e a célula pisca a cada dado novo, pra
// atualização ficar visível de verdade.

export function BadgeAoVivo({ atualizadoEm }: { atualizadoEm: number | null }) {
  // os segundos vivem em estado e só o timer os atualiza — nada de relógio
  // impuro no render. O cronômetro carrega o timestamp a que pertence: quando
  // chega dado novo, a contagem velha é descartada na hora.
  const [cron, setCron] = useState<{ de: number; s: number } | null>(null);
  useEffect(() => {
    if (atualizadoEm == null) return;
    const id = setInterval(
      () =>
        setCron({ de: atualizadoEm, s: Math.max(0, Math.round((Date.now() - atualizadoEm) / 1000)) }),
      1000,
    );
    return () => clearInterval(id);
  }, [atualizadoEm]);
  const s =
    cron && cron.de === atualizadoEm ? cron.s : atualizadoEm != null ? 0 : null;
  return (
    <span className="inline-flex items-stretch overflow-hidden rounded-md border-2 border-emerald-600/80 shadow-[3px_3px_0_rgba(28,26,23,0.12)] dark:border-emerald-500/70 dark:shadow-[3px_3px_0_rgba(0,0,0,0.35)]">
      <span className="flex items-center gap-2 bg-emerald-600 px-3 py-1.5 dark:bg-emerald-500">
        <span className="relative flex h-2 w-2">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-white opacity-70" />
          <span className="relative inline-flex h-2 w-2 rounded-full bg-white" />
        </span>
        <span className="font-display text-[0.8rem] font-bold uppercase leading-none tracking-[0.22em] text-white dark:text-emerald-950">
          ao vivo
        </span>
      </span>
      <span
        key={atualizadoEm ?? "primeira"}
        className="selo-flash num flex items-center bg-emerald-600/10 px-3 text-xs text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400"
      >
        {s == null ? "conectando…" : s === 0 ? "atualizado agora" : `atualizado há ${s}s`}
      </span>
    </span>
  );
}

export function BadgeFrescor({ rotulo, detalhe }: { rotulo: string; detalhe?: string }) {
  return (
    <span className="inline-flex items-stretch overflow-hidden rounded-md border border-ink/35 shadow-[3px_3px_0_rgba(28,26,23,0.08)] dark:shadow-[3px_3px_0_rgba(0,0,0,0.3)]">
      <span className="flex items-center gap-1.5 bg-ink px-2.5 py-1.5 text-bg dark:bg-ink dark:text-bg">
        <RelogioIcone />
        <span className="num text-[0.68rem] font-semibold uppercase leading-none tracking-[0.16em]">
          {rotulo}
        </span>
      </span>
      {detalhe && (
        <span className="num flex items-center bg-surface px-2.5 text-xs leading-none text-muted">
          {detalhe}
        </span>
      )}
    </span>
  );
}

function RelogioIcone() {
  return (
    <svg aria-hidden="true" viewBox="0 0 12 12" className="h-3 w-3 shrink-0">
      <circle cx="6" cy="6" r="4.6" fill="none" stroke="currentColor" strokeWidth="1.2" />
      <path
        d="M6 3.6V6l1.8 1.2"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinecap="round"
      />
    </svg>
  );
}
