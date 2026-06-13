"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { CADERNOS, cadernoAtivo } from "@/lib/cadernos";

export function Indice() {
  const path = usePathname();
  return (
    <aside className="hidden w-52 shrink-0 border-r border-line py-10 pr-6 md:block">
      <nav className="sticky top-24 flex flex-col gap-1">
        <p className="kicker mb-3 pl-1">Cadernos</p>
        {CADERNOS.map((c) => {
          const ativo = cadernoAtivo(path, c.href);
          return (
            <Link
              key={c.href}
              href={c.href}
              aria-current={ativo ? "page" : undefined}
              className={`group flex items-baseline gap-3 rounded-md px-2 py-2 transition-colors ${
                ativo ? "bg-surface" : "hover:bg-surface/70"
              }`}
            >
              <span
                className={`num w-5 shrink-0 text-xs ${ativo ? "text-accent" : "text-muted"}`}
              >
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
        })}
      </nav>
    </aside>
  );
}
