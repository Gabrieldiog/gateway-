import type { FonteDado } from "@/lib/types";

// selo de procedência: diz de qual API oficial o dado veio, com link pra
// conferir. É a resposta pro "não confio, o Google fala outro número".
export function SeloFonte({ fonte }: { fonte?: FonteDado | null }) {
  if (!fonte?.nome) return null;
  return (
    <div className="mt-7 rounded-lg border border-line bg-surface-2/40 p-4">
      <p className="num text-xs uppercase tracking-wider text-muted">
        Fonte oficial ·{" "}
        {fonte.url ? (
          <a
            href={fonte.url}
            target="_blank"
            rel="noreferrer"
            className="text-accent underline decoration-dotted underline-offset-2 hover:text-accent-2"
          >
            {fonte.nome}
          </a>
        ) : (
          <span className="text-ink">{fonte.nome}</span>
        )}
      </p>
      {fonte.nota && (
        <p className="mt-1.5 max-w-[72ch] font-editorial text-sm italic text-ink/70">{fonte.nota}</p>
      )}
    </div>
  );
}
