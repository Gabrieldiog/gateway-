/* eslint-disable @next/next/no-img-element */
import type { ResultadoBusca } from "@/lib/types";
import { AzulejoGlifo } from "./Azulejo";
import { formataData } from "@/lib/api";

const ROTULO: Record<string, string> = {
  deputado: "Deputado federal",
  senador: "Senador",
  proposicao: "Proposição",
  municipio: "Município",
  estado: "Estado",
  serie_economica: "Indicador econômico",
};

function texto(r: ResultadoBusca, campo: string): string | null {
  const v = r[campo];
  return typeof v === "string" || typeof v === "number" ? String(v) : null;
}

export function ResultadoBuscaCard({ r, fonte }: { r: ResultadoBusca; fonte: string }) {
  const tipo = r.tipo_resultado;
  const rotulo = ROTULO[tipo] ?? tipo;
  const foto = texto(r, "foto");
  const nome = texto(r, "nome");

  return (
    <article className="relative flex gap-3 rounded-lg border border-line bg-surface p-3">
      <AzulejoGlifo size={12} className="absolute left-1.5 top-1.5 text-accent-2/30" />

      {(tipo === "deputado" || tipo === "senador") && (
        <div className="h-14 w-12 shrink-0 overflow-hidden rounded-sm border border-line bg-surface-2">
          {foto ? (
            <img src={foto} alt="" loading="lazy" className="h-full w-full object-cover" />
          ) : null}
        </div>
      )}

      <div className="min-w-0 flex-1">
        <p className="kicker mb-0.5 flex items-center gap-1.5">
          <span className="text-accent-2">{fonte}</span>
          <span className="text-line">·</span>
          <span>{rotulo}</span>
        </p>

        {(tipo === "deputado" || tipo === "senador") && (
          <>
            <p className="truncate font-display text-lg leading-tight text-ink">{nome}</p>
            <p className="num text-xs text-muted">
              {[texto(r, "partido"), texto(r, "uf")].filter(Boolean).join(" · ") || "—"}
            </p>
          </>
        )}

        {tipo === "proposicao" && (
          <>
            <p className="num text-sm font-semibold text-ink">
              {texto(r, "tipo")} {texto(r, "numero")}/{texto(r, "ano")}
            </p>
            <p className="mt-0.5 line-clamp-2 font-editorial text-sm leading-snug text-ink/80">
              {texto(r, "ementa") ?? "—"}
            </p>
          </>
        )}

        {(tipo === "municipio" || tipo === "estado") && (
          <>
            <p className="truncate font-display text-lg leading-tight text-ink">{nome}</p>
            <p className="num text-xs text-muted">
              {[texto(r, "sigla"), texto(r, "uf"), texto(r, "regiao")].filter(Boolean).join(" · ") || "—"}
            </p>
          </>
        )}

        {tipo === "serie_economica" && (
          <>
            <p className="font-display text-lg capitalize leading-tight text-ink">
              {texto(r, "nome") ?? `série ${texto(r, "serie")}`}
            </p>
            <p className="num text-xs text-muted">
              <span className="text-ink">{texto(r, "valor")}</span> · {formataData(texto(r, "data"))}
            </p>
          </>
        )}

        {!ROTULO[tipo] && (
          <p className="num mt-1 truncate text-xs text-muted">{JSON.stringify(r)}</p>
        )}
      </div>
    </article>
  );
}
