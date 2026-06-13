"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { CADERNOS, cadernoAtivo } from "@/lib/cadernos";

export function IndiceMobile() {
  const path = usePathname();
  return (
    <nav className="sticky top-[57px] z-20 -mx-4 mb-2 flex gap-1 overflow-x-auto border-b border-line bg-bg/90 px-4 py-2 backdrop-blur-sm md:hidden">
      {CADERNOS.map((c) => {
        const ativo = cadernoAtivo(path, c.href);
        return (
          <Link
            key={c.href}
            href={c.href}
            aria-current={ativo ? "page" : undefined}
            className={`num shrink-0 rounded-full border px-3 py-1 text-xs uppercase tracking-wider transition-colors ${
              ativo
                ? "border-accent bg-accent text-surface"
                : "border-line text-muted"
            }`}
          >
            {c.nome}
          </Link>
        );
      })}
    </nav>
  );
}
