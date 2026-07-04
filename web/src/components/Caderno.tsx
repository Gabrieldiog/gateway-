"use client";

import { usePathname } from "next/navigation";
import { numeroDoPath } from "@/lib/cadernos";
import { frescorDoPath } from "@/lib/frescor";
import { BadgeFrescor } from "./Frescor";
import { azulejoFundo } from "./Azulejo";

// abre cada seção: marca-d'água de azulejo, kicker em mono, manchete em
// Fraunces e a régua dupla que se desenha ao entrar. O número é derivado da
// posição do caderno no grupo (via pathname), não fixado na página — cada tema
// recomeça em I, II, III. O prop `numero` é só reserva pra página fora do sumário.
// Abaixo da régua vem o selo de frescor: de quanto em quanto tempo aquela fonte
// solta dado novo — a dateline do caderno (páginas ao vivo trazem o próprio selo).
export function CadernoHeader({
  numero,
  kicker,
  titulo,
  resumo,
}: {
  numero?: string;
  kicker: string;
  titulo: string;
  resumo?: string;
}) {
  const path = usePathname();
  const num = numeroDoPath(path) || numero || "";
  const fresco = frescorDoPath(path);
  return (
    <header className="mb-6">
      <div className="relative overflow-hidden">
        <div
          className="azulejo-marca pointer-events-none absolute -right-4 -top-6 h-28 w-64"
          style={azulejoFundo(0.06)}
          aria-hidden="true"
        />
        <p className="kicker mb-2 flex items-center gap-2">
          <span className="text-accent">CADERNO {num}</span>
          <span className="text-line">—</span>
          <span>{kicker}</span>
        </p>
        <h1 className="compor font-display text-4xl font-semibold leading-[1.05] tracking-tight text-ink sm:text-5xl">
          {titulo}
        </h1>
        {resumo && (
          <p className="mt-3 max-w-[60ch] font-editorial text-[1.05rem] leading-relaxed text-ink/80">
            {resumo}
          </p>
        )}
        <div className="regua-dupla desenha-regua mt-5" />
      </div>
      {fresco && (
        <div className="mt-3">
          <BadgeFrescor rotulo={fresco.rotulo} detalhe={fresco.detalhe} />
        </div>
      )}
    </header>
  );
}
