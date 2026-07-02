"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { CAPA, GRUPOS, cadernoAtivo, type Caderno } from "@/lib/cadernos";

// no celular o sumário vira um baralho de dois níveis: a primeira linha são
// os temas, a segunda os cadernos do tema tocado. O tema da página atual
// já vem selecionado; navegar pra outro grupo re-seleciona (ajuste no
// render, sem effect).
export function IndiceMobile() {
  const path = usePathname();
  const grupoDoPath =
    GRUPOS.find((g) => g.cadernos.some((c) => cadernoAtivo(path, c.href)))?.nome ?? null;
  const [escolha, setEscolha] = useState<string | null | undefined>(undefined);
  const [grupoVisto, setGrupoVisto] = useState(grupoDoPath);
  if (grupoVisto !== grupoDoPath) {
    setGrupoVisto(grupoDoPath);
    setEscolha(undefined);
  }
  const grupo = escolha === undefined ? grupoDoPath : escolha;

  const aberto = GRUPOS.find((g) => g.nome === grupo);

  return (
    <nav className="sticky top-[57px] z-20 -mx-4 mb-2 border-b border-line bg-bg/90 backdrop-blur-sm md:hidden">
      <div className="flex items-center gap-1.5 overflow-x-auto px-4 pb-1.5 pt-2">
        <ChipCaderno c={CAPA} ativo={cadernoAtivo(path, CAPA.href)} />
        {GRUPOS.map((g) => {
          const selecionado = g.nome === grupo;
          return (
            <button
              key={g.nome}
              onClick={() => setEscolha(selecionado ? null : g.nome)}
              aria-expanded={selecionado}
              className={`num flex shrink-0 items-center gap-1.5 rounded-full border px-3 py-1 text-xs uppercase tracking-wider transition-colors ${
                selecionado
                  ? "border-ink bg-ink text-bg"
                  : g.nome === grupoDoPath
                    ? "border-accent/60 text-accent"
                    : "border-line text-muted"
              }`}
            >
              {g.nome}
              <svg
                aria-hidden="true"
                viewBox="0 0 12 12"
                className={`h-2 w-2 transition-transform duration-200 ${selecionado ? "rotate-180" : ""}`}
              >
                <path
                  d="M2.5 4.5 6 8l3.5-3.5"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </button>
          );
        })}
      </div>
      {aberto && (
        <div className="flex items-center gap-1.5 overflow-x-auto px-4 pb-2 pt-0.5">
          {aberto.cadernos.map((c) => (
            <ChipCaderno key={c.href} c={c} ativo={cadernoAtivo(path, c.href)} />
          ))}
        </div>
      )}
    </nav>
  );
}

function ChipCaderno({ c, ativo }: { c: Caderno; ativo: boolean }) {
  return (
    <Link
      href={c.href}
      aria-current={ativo ? "page" : undefined}
      className={`num shrink-0 rounded-full border px-3 py-1 text-xs uppercase tracking-wider transition-colors ${
        ativo ? "border-accent bg-accent text-surface" : "border-line text-muted"
      }`}
    >
      {c.nome}
    </Link>
  );
}
