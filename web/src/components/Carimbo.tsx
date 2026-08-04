// carimbo cartorial funcional: mostra o estado REAL da resposta, a fonte,
// se veio do cache (hit/miss/stale) e a latência medida. a resiliência do
// gateway aparece como feature, não fica escondida.

export function Carimbo({
  fonte,
  cache,
  ms,
  erro = false,
}: {
  fonte: string;
  cache?: string | null;
  ms?: number | null;
  erro?: boolean;
}) {
  const cor = erro
    ? "text-erro border-erro/60"
    : cache === "hit"
      ? "text-ok border-ok/50"
      : cache === "stale"
        ? "text-ocre border-ocre/60"
        : "text-accent-2 border-accent-2/45";

  const estado = erro
    ? "INDISPONÍVEL"
    : cache === "hit"
      ? "CACHE HIT"
      : cache === "stale"
        ? "DO ARQUIVO"
        : "DIRETO";

  return (
    <span
      className={`num inline-flex shrink-0 select-none items-center gap-1.5 rounded-sm border border-dashed px-2 py-0.5 text-[0.62rem] uppercase tracking-[0.12em] ${cor} ${
        erro ? "carimbo-shake" : ""
      }`}
      style={{ transform: "rotate(-2deg)" }}
    >
      <span className="font-semibold">{fonte}</span>
      <span className="opacity-50">·</span>
      <span>{estado}</span>
      {ms != null && !erro && (
        <>
          <span className="opacity-50">·</span>
          <span>{ms}ms</span>
        </>
      )}
    </span>
  );
}
