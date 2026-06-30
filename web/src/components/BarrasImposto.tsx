import { formataBRL } from "@/lib/api";
import type { Imposto } from "@/lib/types";

// quebra da arrecadação por imposto: a sigla em destaque (mono, caixa alta),
// o nome inteiro embaixo, e a barra proporcional. o maior leva o acento.
export function BarrasImposto({ impostos }: { impostos: Imposto[] }) {
  const itens = [...impostos].sort((a, b) => Number(b.valor) - Number(a.valor));
  const max = Number(itens[0]?.valor ?? 1);

  if (!itens.length) {
    return <p className="font-editorial italic text-muted">sem impostos no período.</p>;
  }

  return (
    <ul className="flex flex-col gap-4">
      {itens.map((it, i) => (
        <li key={it.sigla}>
          <div className="mb-1 flex items-baseline justify-between gap-3">
            <span
              className={`num text-sm font-semibold uppercase tracking-wide ${i === 0 ? "text-accent" : "text-ink"}`}
              title={it.nome}
            >
              {it.sigla === "OUTROS" ? "outros" : it.sigla}
            </span>
            <span className={`num shrink-0 text-sm ${i === 0 ? "text-accent" : "text-ink"}`}>
              {formataBRL(Number(it.valor))}
            </span>
          </div>
          <div className="h-2 overflow-hidden rounded-sm bg-surface-2">
            <div
              className={`h-full rounded-sm ${i === 0 ? "bg-accent" : "bg-ink/70"}`}
              style={{ width: `${Math.max((Number(it.valor) / max) * 100, 1.5)}%` }}
            />
          </div>
          <span className="mt-1 block truncate text-[0.72rem] text-muted" title={it.nome}>
            {it.nome}
          </span>
        </li>
      ))}
    </ul>
  );
}
