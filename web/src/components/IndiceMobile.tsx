"use client";

import { Fragment } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { CAPA, GRUPOS, cadernoAtivo, type Caderno } from "@/lib/cadernos";

export function IndiceMobile() {
  const path = usePathname();
  return (
    <nav className="sticky top-[57px] z-20 -mx-4 mb-2 flex items-center gap-1 overflow-x-auto border-b border-line bg-bg/90 px-4 py-2 backdrop-blur-sm md:hidden">
      <Chip c={CAPA} ativo={cadernoAtivo(path, CAPA.href)} />
      {GRUPOS.map((g) => (
        <Fragment key={g.nome}>
          <span className="num shrink-0 pl-2 pr-0.5 text-[0.58rem] uppercase tracking-wider text-muted/70">
            {g.nome}
          </span>
          {g.cadernos.map((c) => (
            <Chip key={c.href} c={c} ativo={cadernoAtivo(path, c.href)} />
          ))}
        </Fragment>
      ))}
    </nav>
  );
}

function Chip({ c, ativo }: { c: Caderno; ativo: boolean }) {
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
