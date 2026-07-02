"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { CAPA, GRUPOS, cadernoAtivo, type Caderno } from "@/lib/cadernos";

// o sumário cresceu: cada tema agora é uma gaveta. A da página atual abre
// sozinha; as outras ficam fechadas até o leitor querer.
export function Indice() {
  const path = usePathname();
  const grupoDoPath =
    GRUPOS.find((g) => g.cadernos.some((c) => cadernoAtivo(path, c.href)))?.nome ?? null;

  // sem toggle explícito, a gaveta aberta é a da página atual; ao navegar pra
  // outro grupo, o toggle fechado do novo grupo é esquecido (ajuste no render,
  // sem effect)
  const [toggles, setToggles] = useState<Record<string, boolean>>({});
  const [grupoVisto, setGrupoVisto] = useState(grupoDoPath);
  if (grupoVisto !== grupoDoPath) {
    setGrupoVisto(grupoDoPath);
    if (grupoDoPath && toggles[grupoDoPath] === false) {
      setToggles((t) => ({ ...t, [grupoDoPath]: true }));
    }
  }
  const estaAberto = (nome: string) => toggles[nome] ?? nome === grupoDoPath;

  const alterna = (nome: string) =>
    setToggles((t) => ({ ...t, [nome]: !estaAberto(nome) }));

  return (
    <aside className="hidden w-52 shrink-0 border-r border-line py-10 pr-6 md:block">
      <nav className="sticky top-24 flex flex-col gap-2">
        <ItemCaderno c={CAPA} ativo={cadernoAtivo(path, CAPA.href)} />
        {GRUPOS.map((g) => {
          const aberto = estaAberto(g.nome);
          const temAtivo = g.nome === grupoDoPath;
          return (
            <div key={g.nome}>
              <button
                onClick={() => alterna(g.nome)}
                aria-expanded={aberto}
                className="group flex w-full items-center gap-2 rounded-md px-2 py-1.5 transition-colors hover:bg-surface/70"
              >
                <span
                  className={`kicker transition-colors group-hover:text-ink ${
                    temAtivo ? "text-accent" : ""
                  }`}
                >
                  {g.nome}
                </span>
                <span className="h-px min-w-3 flex-1 bg-line" />
                <span className="num text-[0.6rem] text-muted/70">{g.cadernos.length}</span>
                <svg
                  aria-hidden="true"
                  viewBox="0 0 12 12"
                  className={`h-2.5 w-2.5 shrink-0 text-muted transition-transform duration-200 ${
                    aberto ? "rotate-180" : ""
                  }`}
                >
                  <path
                    d="M2.5 4.5 6 8l3.5-3.5"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.6"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </button>
              <div
                className={`grid transition-[grid-template-rows] duration-300 ease-out ${
                  aberto ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
                }`}
              >
                <div className="flex flex-col gap-0.5 overflow-hidden">
                  {g.cadernos.map((c) => (
                    <ItemCaderno key={c.href} c={c} ativo={cadernoAtivo(path, c.href)} />
                  ))}
                </div>
              </div>
            </div>
          );
        })}
      </nav>
    </aside>
  );
}

function ItemCaderno({ c, ativo }: { c: Caderno; ativo: boolean }) {
  return (
    <Link
      href={c.href}
      aria-current={ativo ? "page" : undefined}
      className={`group flex items-baseline gap-3 rounded-md px-2 py-2 transition-colors ${
        ativo ? "bg-surface" : "hover:bg-surface/70"
      }`}
    >
      <span className={`num w-5 shrink-0 text-xs ${ativo ? "text-accent" : "text-muted"}`}>
        {c.num}
      </span>
      <span className="flex flex-col leading-tight">
        <span
          className={`font-display text-[1.05rem] ${
            ativo ? "font-semibold text-ink" : "text-ink/85"
          }`}
        >
          {c.nome}
        </span>
        <span className="text-[0.72rem] text-muted">{c.sub}</span>
      </span>
      {ativo && <span className="ml-auto h-1.5 w-1.5 self-center rounded-full bg-accent" />}
    </Link>
  );
}
