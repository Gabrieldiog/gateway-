"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { CAPA, GRUPOS, cadernoAtivo, type Caderno } from "@/lib/cadernos";

export function Indice() {
  const path = usePathname();
  return (
    <aside className="hidden w-52 shrink-0 border-r border-line py-10 pr-6 md:block">
      <nav className="sticky top-24 flex flex-col gap-5">
        <ItemCaderno c={CAPA} ativo={cadernoAtivo(path, CAPA.href)} />
        {GRUPOS.map((g) => (
          <div key={g.nome} className="flex flex-col gap-0.5">
            <p className="kicker mb-1.5 pl-2">{g.nome}</p>
            {g.cadernos.map((c) => (
              <ItemCaderno key={c.href} c={c} ativo={cadernoAtivo(path, c.href)} />
            ))}
          </div>
        ))}
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
