"use client";

import { useContagem } from "@/hooks/useContagem";
import { formataBRL } from "@/lib/api";

// número-herói em Fraunces com count-up na montagem.
export function Kpi({
  rotulo,
  valor,
  formato = "inteiro",
  sufixo,
  tom = "ink",
}: {
  rotulo: string;
  valor: number;
  formato?: "inteiro" | "brl" | "decimal";
  sufixo?: string;
  tom?: "ink" | "accent" | "accent-2";
}) {
  const n = useContagem(valor);
  const corNumero =
    tom === "accent" ? "text-accent" : tom === "accent-2" ? "text-accent-2" : "text-ink";

  let texto: string;
  if (formato === "brl") texto = formataBRL(n);
  else if (formato === "decimal") texto = n.toLocaleString("pt-BR", { maximumFractionDigits: 2 });
  else texto = Math.round(n).toLocaleString("pt-BR");

  return (
    <div className="flex flex-col">
      <span className="kicker mb-1">{rotulo}</span>
      <span className={`font-display text-4xl font-semibold leading-none tracking-tight sm:text-5xl ${corNumero}`}>
        {texto}
        {sufixo && <span className="num ml-1.5 align-baseline text-base text-muted">{sufixo}</span>}
      </span>
    </div>
  );
}
