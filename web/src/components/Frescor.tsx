"use client";

import { useEffect, useState } from "react";

// selo de frescor dos cadernos: diz com que cadência o dado se renova — e,
// nos ao-vivo, mostra o relógio andando pra atualização ficar visível
// ("está atualizando o tempo todo, mas pro usuário nem parece").

export function BadgeAoVivo({ atualizadoEm }: { atualizadoEm: number | null }) {
  const [, tique] = useState(0);
  useEffect(() => {
    const id = setInterval(() => tique((n) => n + 1), 1000);
    return () => clearInterval(id);
  }, []);
  const s = atualizadoEm == null ? null : Math.max(0, Math.round((Date.now() - atualizadoEm) / 1000));
  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-emerald-500/40 bg-emerald-500/10 px-3 py-1">
      <span className="relative flex h-2 w-2">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-500 opacity-75" />
        <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
      </span>
      <span className="num text-xs font-semibold uppercase tracking-wider text-emerald-600">
        ao vivo
        {s != null && (
          <span className="ml-1.5 font-normal normal-case tracking-normal text-emerald-700/80">
            · atualizado há {s}s
          </span>
        )}
      </span>
    </span>
  );
}

export function BadgeFrescor({ rotulo, detalhe }: { rotulo: string; detalhe?: string }) {
  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-line bg-surface-2/60 px-3 py-1">
      <span className="inline-flex h-2 w-2 rounded-full bg-muted/60" />
      <span className="num text-xs font-semibold uppercase tracking-wider text-muted">
        {rotulo}
        {detalhe && <span className="ml-1.5 font-normal normal-case tracking-normal">· {detalhe}</span>}
      </span>
    </span>
  );
}
