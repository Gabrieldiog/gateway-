"use client";

import { useEffect, useRef, useState } from "react";
import { GLOSSARIO } from "@/lib/glossario";

// o "o que é isso?" do jornal: sublinha o jargão com pontilhado e, no
// clique/toque, abre um verbete curto. Termo desconhecido passa reto,
// sem sublinhar — dá pra usar com chave dinâmica sem medo.
export function Termo({ t, children }: { t: string; children: React.ReactNode }) {
  const def = GLOSSARIO[t];
  const [aberto, setAberto] = useState(false);
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (!aberto) return;
    const fora = (e: MouseEvent | TouchEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setAberto(false);
    };
    const esc = (e: KeyboardEvent) => {
      if (e.key === "Escape") setAberto(false);
    };
    document.addEventListener("mousedown", fora);
    document.addEventListener("touchstart", fora);
    document.addEventListener("keydown", esc);
    return () => {
      document.removeEventListener("mousedown", fora);
      document.removeEventListener("touchstart", fora);
      document.removeEventListener("keydown", esc);
    };
  }, [aberto]);

  if (!def) return <>{children}</>;

  return (
    <span ref={ref} className="relative inline-block">
      <button
        type="button"
        onClick={() => setAberto((a) => !a)}
        aria-expanded={aberto}
        className="cursor-help border-b border-dotted border-muted/80 transition-colors hover:border-accent hover:text-accent"
      >
        {children}
      </button>
      {aberto && (
        <span
          role="note"
          className="absolute left-1/2 top-full z-30 mt-2 block w-72 max-w-[80vw] -translate-x-1/2 rounded-md border border-line bg-surface p-3.5 text-left shadow-lg"
        >
          <span className="block font-display text-sm font-semibold normal-case tracking-normal text-ink">
            {def.titulo}
          </span>
          <span className="mt-1.5 block font-editorial text-[0.85rem] font-normal normal-case leading-relaxed tracking-normal text-ink/80">
            {def.texto}
          </span>
        </span>
      )}
    </span>
  );
}
