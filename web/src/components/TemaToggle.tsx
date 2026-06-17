"use client";

import { useEffect, useState } from "react";
import { useTheme } from "next-themes";

export function TemaToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const [montado, setMontado] = useState(false);

  // o tema só é conhecido no cliente; até montar, render neutro pra não dar
  // mismatch de hidratação (servidor e 1ª render do cliente batem em "edição").
  useEffect(() => setMontado(true), []);

  const escuro = montado && resolvedTheme === "dark";
  const rotulo = !montado ? "edição" : escuro ? "noturna" : "diurna";

  return (
    <button
      type="button"
      onClick={() => setTheme(escuro ? "light" : "dark")}
      aria-label={escuro ? "Mudar para edição diurna" : "Mudar para edição noturna"}
      className="num flex items-center gap-1.5 rounded-full border border-line px-2.5 py-1 text-[0.7rem] uppercase tracking-wider text-muted transition-colors hover:border-accent/50 hover:text-ink"
    >
      <Glifo escuro={escuro} montado={montado} />
      <span className="hidden sm:inline">{rotulo}</span>
    </button>
  );
}

function Glifo({ escuro, montado }: { escuro: boolean; montado: boolean }) {
  if (!montado) {
    return <span className="inline-block h-3.5 w-3.5 rounded-full border border-current opacity-50" />;
  }
  return escuro ? <Sol /> : <Lua />;
}

function Lua() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
    </svg>
  );
}

function Sol() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
    </svg>
  );
}
