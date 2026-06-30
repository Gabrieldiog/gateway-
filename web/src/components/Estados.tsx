import type { BalcaoError } from "@/lib/api";

// o carregando padrão: um spinner em loop, bem visível (inclusive no escuro)
export function Carregando({ texto = "carregando", min }: { texto?: string; min?: number }) {
  return (
    <div
      className="flex flex-col items-center justify-center gap-3 py-10"
      style={min ? { minHeight: min } : undefined}
      role="status"
      aria-live="polite"
      aria-label="carregando"
    >
      <span className="h-9 w-9 animate-spin rounded-full border-[3px] border-line border-t-accent" />
      <span className="num text-xs uppercase tracking-wider text-muted">{texto}…</span>
    </div>
  );
}

// mantém o nome usado nos cadernos; antes era um skeleton de barras (sumia no
// modo escuro), agora reserva a altura equivalente e mostra o spinner.
export function Esqueleto({ linhas = 5 }: { linhas?: number }) {
  return <Carregando min={linhas * 44} />;
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

// quando um filtro muda, o useBalcao segura os dados antigos enquanto rebusca —
// sem isso a tela parece travada. O conteúdo velho esmaece e o mesmo spinner do
// carregando aparece centralizado por cima, deixando claro que tem coisa vindo.
export function EmTransicao({ ativo, children }: { ativo: boolean; children: React.ReactNode }) {
  return (
    <div className="relative">
      <div
        className={`transition-opacity duration-200 ${ativo ? "pointer-events-none opacity-30" : "opacity-100"}`}
        aria-busy={ativo}
      >
        {children}
      </div>
      {ativo && (
        <div className="pointer-events-none absolute inset-x-0 top-12 z-10 flex justify-center">
          <span className="flex items-center gap-2.5 rounded-full border border-line bg-surface/95 px-4 py-2 shadow-sm backdrop-blur-sm">
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-line border-t-accent" />
            <span className="num text-xs uppercase tracking-wider text-muted">carregando…</span>
          </span>
        </div>
      )}
    </div>
  );
}
