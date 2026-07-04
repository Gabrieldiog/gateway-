"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { CAPA, GRUPOS, cadernoAtivo, numeroDoCaderno, type Caderno } from "@/lib/cadernos";

// no celular o sumário inteiro é grande demais pra caber sempre à vista: vira
// um menu-gaveta atrás de um botão de três traços. A gaveta desliza da
// esquerda, escurece o fundo, e fecha ao navegar, tocar fora ou apertar Esc.
export function MenuMobile() {
  const path = usePathname();
  const [aberto, setAberto] = useState(false);
  const grupoDoPath =
    GRUPOS.find((g) => g.cadernos.some((c) => cadernoAtivo(path, c.href)))?.nome ?? null;

  // trava o scroll do fundo e escuta o Esc só enquanto a gaveta está aberta
  useEffect(() => {
    if (!aberto) return;
    const anterior = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    function tecla(e: KeyboardEvent) {
      if (e.key === "Escape") setAberto(false);
    }
    document.addEventListener("keydown", tecla);
    return () => {
      document.body.style.overflow = anterior;
      document.removeEventListener("keydown", tecla);
    };
  }, [aberto]);

  const fecha = () => setAberto(false);

  return (
    <div className="md:hidden">
      <button
        type="button"
        onClick={() => setAberto(true)}
        aria-label="Abrir o sumário"
        aria-expanded={aberto}
        className="flex min-h-11 min-w-11 items-center justify-center rounded-md border border-line text-ink transition-colors hover:border-accent"
      >
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true">
          <path d="M3 5h14M3 10h14M3 15h14" />
        </svg>
      </button>

      {/* a gaveta vai pro <body> via portal: o cabeçalho tem backdrop-blur, que
          cria um containing block e prenderia um position:fixed ali dentro —
          fora do header, o inset-0 volta a valer pela viewport inteira */}
      {aberto &&
        createPortal(
          <div className="fixed inset-0 z-[60] md:hidden">
            <button
              aria-label="Fechar o sumário"
              onClick={fecha}
              className="absolute inset-0 bg-ink/40 backdrop-blur-[2px]"
            />
            <div className="absolute inset-y-0 left-0 flex w-[86%] max-w-sm flex-col border-r border-line bg-bg shadow-2xl">
              <div className="flex items-center justify-between border-b border-line px-5 py-4">
                <span className="font-display text-lg font-semibold tracking-[0.1em] text-ink">SUMÁRIO</span>
                <button
                  type="button"
                  onClick={fecha}
                  aria-label="Fechar"
                  className="flex min-h-11 min-w-11 items-center justify-center rounded-md text-muted transition-colors hover:text-ink"
                >
                  <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true">
                    <path d="M4 4l10 10M14 4L4 14" />
                  </svg>
                </button>
              </div>

              <nav className="flex flex-1 flex-col gap-1 overflow-y-auto px-3 py-4">
                <ItemGaveta c={CAPA} ativo={cadernoAtivo(path, CAPA.href)} aoNavegar={fecha} />
                {GRUPOS.map((g) => (
                  <Grupo
                    key={g.nome}
                    nome={g.nome}
                    cadernos={g.cadernos}
                    abreInicial={g.nome === grupoDoPath}
                    path={path}
                    aoNavegar={fecha}
                  />
                ))}
              </nav>
            </div>
          </div>,
          document.body,
        )}
    </div>
  );
}

function Grupo({
  nome,
  cadernos,
  abreInicial,
  path,
  aoNavegar,
}: {
  nome: string;
  cadernos: Caderno[];
  abreInicial: boolean;
  path: string;
  aoNavegar: () => void;
}) {
  const [aberto, setAberto] = useState(abreInicial);
  return (
    <div>
      <button
        type="button"
        onClick={() => setAberto((v) => !v)}
        aria-expanded={aberto}
        className="flex min-h-11 w-full items-center gap-2 px-2"
      >
        <span className={`kicker ${abreInicial ? "text-accent" : ""}`}>{nome}</span>
        <span className="h-px min-w-3 flex-1 bg-line" />
        <svg
          aria-hidden="true"
          viewBox="0 0 12 12"
          className={`h-2.5 w-2.5 shrink-0 text-muted transition-transform duration-200 ${aberto ? "rotate-180" : ""}`}
        >
          <path d="M2.5 4.5 6 8l3.5-3.5" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>
      {aberto && (
        <div className="mb-1 flex flex-col">
          {cadernos.map((c) => (
            <ItemGaveta key={c.href} c={c} ativo={cadernoAtivo(path, c.href)} aoNavegar={aoNavegar} />
          ))}
        </div>
      )}
    </div>
  );
}

function ItemGaveta({ c, ativo, aoNavegar }: { c: Caderno; ativo: boolean; aoNavegar: () => void }) {
  return (
    <Link
      href={c.href}
      onClick={aoNavegar}
      aria-current={ativo ? "page" : undefined}
      className={`flex min-h-11 items-baseline gap-3 rounded-md px-2 py-2 transition-colors ${
        ativo ? "bg-surface" : "active:bg-surface/70"
      }`}
    >
      <span className={`num w-5 shrink-0 text-xs ${ativo ? "text-accent" : "text-muted"}`}>
        {numeroDoCaderno(c.href)}
      </span>
      <span className="flex flex-col leading-tight">
        <span className={`font-display text-base ${ativo ? "font-semibold text-ink" : "text-ink/85"}`}>
          {c.nome}
        </span>
        <span className="text-[0.72rem] text-muted">{c.sub}</span>
      </span>
    </Link>
  );
}
