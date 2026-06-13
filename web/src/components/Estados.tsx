import type { BalcaoError } from "@/lib/api";

export function Esqueleto({ linhas = 5 }: { linhas?: number }) {
  return (
    <div className="space-y-2" aria-busy="true" aria-label="carregando">
      {Array.from({ length: linhas }).map((_, i) => (
        <div
          key={i}
          className="pulsar h-11 rounded-md bg-surface-2"
          style={{ animationDelay: `${i * 90}ms` }}
        />
      ))}
    </div>
  );
}

export function ErroBox({ erro, aoTentar }: { erro: BalcaoError; aoTentar?: () => void }) {
  const disponiveis =
    (erro.detalhes?.fontes_disponiveis as string[] | undefined) ??
    (erro.detalhes?.recursos_disponiveis as string[] | undefined) ??
    (erro.detalhes?.parametros_aceitos as string[] | undefined);
  return (
    <div className="rounded-lg border border-dashed border-erro/50 bg-erro/5 p-5">
      <p className="num text-xs uppercase tracking-wider text-erro">
        falha {erro.status > 0 ? `· ${erro.status}` : ""}
      </p>
      <p className="mt-1 font-editorial text-lg text-ink">{erro.message}</p>
      {disponiveis && (
        <p className="mt-2 text-sm text-muted">
          disponíveis: <span className="num text-ink">{disponiveis.join(", ")}</span>
        </p>
      )}
      {aoTentar && (
        <button
          onClick={aoTentar}
          className="num mt-4 rounded-md border border-ink/20 px-3 py-1 text-xs uppercase tracking-wider text-ink transition-colors hover:bg-surface-2"
        >
          tentar de novo
        </button>
      )}
    </div>
  );
}

export function Vazio({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-dashed border-line bg-surface/50 p-8 text-center">
      <p className="font-editorial text-lg italic text-muted">{children}</p>
    </div>
  );
}
