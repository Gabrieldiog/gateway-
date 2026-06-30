import { formataBRL, formataReaisCompacto } from "@/lib/api";

// ranking de gastos por tipo em barras finas; o maior recebe o acento, o
// resto fica em tinta. valores em mono na ponta, como gráfico de jornal.
// compacto=true encurta os valores (R$ 1,9 bi) — útil pra cifras grandes.
export function BarrasGasto({
  porTipo,
  compacto = false,
}: {
  porTipo: Record<string, string>;
  compacto?: boolean;
}) {
  const itens = Object.entries(porTipo)
    .map(([tipo, valor]) => ({ tipo, valor: Number(valor) }))
    .sort((a, b) => b.valor - a.valor);
  const max = itens[0]?.valor ?? 1;
  const fmt = compacto ? formataReaisCompacto : formataBRL;

  if (!itens.length) {
    return <p className="font-editorial italic text-muted">sem despesas no período.</p>;
  }

  return (
    <ul className="flex flex-col gap-3">
      {itens.map((it, i) => (
        <li key={it.tipo}>
          <div className="mb-1 flex items-baseline justify-between gap-3">
            <span className="truncate text-sm text-ink/85" title={it.tipo}>
              {it.tipo.toLowerCase()}
            </span>
            <span className={`num shrink-0 text-sm ${i === 0 ? "text-accent" : "text-ink"}`}>
              {fmt(it.valor)}
            </span>
          </div>
          <div className="h-2 overflow-hidden rounded-sm bg-surface-2">
            <div
              className={`h-full rounded-sm ${i === 0 ? "bg-accent" : "bg-ink/70"}`}
              style={{ width: `${Math.max((it.valor / max) * 100, 1.5)}%` }}
            />
          </div>
        </li>
      ))}
    </ul>
  );
}
