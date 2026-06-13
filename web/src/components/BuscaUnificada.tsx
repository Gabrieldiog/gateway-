"use client";

import { useRef, useState } from "react";
import { apiGet, BalcaoError, caminho } from "@/lib/api";
import type { BuscaOut, ResultadoBusca } from "@/lib/types";
import { ResultadoBuscaCard } from "./ResultadoBuscaCard";

const FONTES = [
  { id: "camara", nome: "Câmara" },
  { id: "senado", nome: "Senado" },
  { id: "bacen", nome: "Banco Central" },
  { id: "ibge", nome: "IBGE" },
];

const SUGESTOES = ["Marina", "Selic", "Campinas", "educação"];

type Status = "pendente" | "ok" | "erro";
interface EstadoFonte {
  id: string;
  nome: string;
  status: Status;
  ms: number | null;
  resultados: ResultadoBusca[];
  msg?: string;
}

export function BuscaUnificada() {
  const [termo, setTermo] = useState("");
  const [enviado, setEnviado] = useState<string | null>(null);
  const [fontes, setFontes] = useState<EstadoFonte[]>([]);
  const token = useRef(0);

  async function buscar(q: string) {
    const limpo = q.trim();
    if (limpo.length < 2) return;
    const meu = ++token.current;
    setEnviado(limpo);
    setFontes(FONTES.map((f) => ({ ...f, status: "pendente", ms: null, resultados: [] })));

    // dispara uma requisição por fonte em paralelo; cada uma pinta sua coluna
    // assim que retorna, tornando o fan-out e a resiliência visíveis ao vivo.
    await Promise.all(
      FONTES.map(async (f) => {
        const t0 = performance.now();
        try {
          const r = await apiGet<BuscaOut>(caminho("buscar", { q: limpo, fontes: f.id }));
          if (meu !== token.current) return;
          const ms = Math.round(performance.now() - t0);
          const falhou = r.erros?.[f.id];
          setFontes((prev) =>
            prev.map((x) =>
              x.id === f.id
                ? { ...x, status: falhou ? "erro" : "ok", ms, resultados: r.resultados, msg: falhou }
                : x,
            ),
          );
        } catch (e) {
          if (meu !== token.current) return;
          const ms = Math.round(performance.now() - t0);
          const msg = e instanceof BalcaoError ? e.message : "falha de rede";
          setFontes((prev) =>
            prev.map((x) => (x.id === f.id ? { ...x, status: "erro", ms, msg } : x)),
          );
        }
      }),
    );
  }

  const total = fontes.reduce((s, f) => s + f.resultados.length, 0);
  const concluido = enviado && fontes.every((f) => f.status !== "pendente");

  return (
    <section>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          buscar(termo);
        }}
        className="relative"
      >
        <div className="flex items-center gap-2 rounded-xl border-2 border-ink bg-surface px-4 py-3 shadow-[3px_3px_0_0_var(--color-ink)] transition-all focus-within:translate-x-0.5 focus-within:translate-y-0.5 focus-within:border-accent focus-within:shadow-[1px_1px_0_0_var(--color-accent)]">
          <span className="num text-sm text-muted">⌕</span>
          <input
            value={termo}
            onChange={(e) => setTermo(e.target.value)}
            placeholder="busque um nome, um indicador, um município…"
            className="min-w-0 flex-1 bg-transparent font-editorial text-lg text-ink outline-none placeholder:text-muted"
            aria-label="termo de busca"
          />
          <button
            type="submit"
            className="num shrink-0 rounded-md bg-accent px-4 py-1.5 text-xs font-semibold uppercase tracking-widest text-surface transition-opacity hover:opacity-90"
          >
            buscar
          </button>
        </div>
      </form>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <span className="kicker">tente</span>
        {SUGESTOES.map((s) => (
          <button
            key={s}
            onClick={() => {
              setTermo(s);
              buscar(s);
            }}
            className="num rounded-full border border-line px-3 py-0.5 text-xs text-muted transition-colors hover:border-accent-2 hover:text-accent-2"
          >
            {s}
          </button>
        ))}
      </div>

      {enviado && (
        <>
          <div className="mt-6 flex flex-wrap items-center gap-2">
            {fontes.map((f) => (
              <ChipFonte key={f.id} f={f} />
            ))}
            {concluido && (
              <span className="num ml-auto text-xs text-muted">
                {total} resultado{total === 1 ? "" : "s"} de “{enviado}”
              </span>
            )}
          </div>

          <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2">
            {fontes.flatMap((f) =>
              f.resultados.map((r, i) => (
                <div
                  key={`${f.id}-${i}`}
                  className="imprime"
                  style={{ animationDelay: `${Math.min(i, 8) * 35}ms` }}
                >
                  <ResultadoBuscaCard r={r} fonte={f.nome} />
                </div>
              )),
            )}
          </div>

          {concluido && total === 0 && (
            <p className="mt-6 font-editorial text-lg italic text-muted">
              nenhuma fonte tinha algo para “{enviado}”. tente outro termo.
            </p>
          )}
        </>
      )}
    </section>
  );
}

function ChipFonte({ f }: { f: EstadoFonte }) {
  const cor =
    f.status === "ok"
      ? "border-ok/50 text-ok"
      : f.status === "erro"
        ? "border-erro/50 text-erro"
        : "border-line text-muted";
  return (
    <span
      className={`num inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs ${cor}`}
      title={f.msg}
    >
      <span
        className={`inline-block h-1.5 w-1.5 rounded-full ${
          f.status === "ok" ? "bg-ok" : f.status === "erro" ? "bg-erro" : "bg-muted pulsar"
        }`}
      />
      <span className="text-ink">{f.nome}</span>
      {f.status === "pendente" && <span>consultando…</span>}
      {f.status === "ok" && (
        <span>
          ✓ {f.ms}ms · {f.resultados.length}
        </span>
      )}
      {f.status === "erro" && <span>✗ caiu · serve cache</span>}
    </span>
  );
}
