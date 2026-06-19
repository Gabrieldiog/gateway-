"use client";

import { useEffect, useState } from "react";
import { CadernoHeader } from "@/components/Caderno";
import { Card } from "@/components/Card";
import { Carimbo } from "@/components/Carimbo";
import { Kpi } from "@/components/Kpi";
import { SerieChart } from "@/components/SerieChart";
import { Esqueleto, ErroBox, Vazio } from "@/components/Estados";
import { useBalcao } from "@/hooks/useBalcao";
import { caminho, formataData } from "@/lib/api";
import type { NormalizedResponse, PontoIpea, SerieIpea } from "@/lib/types";

const JANELAS = [24, 48, 120];

export default function CadernoIpea() {
  const [texto, setTexto] = useState("IPCA");
  const [q, setQ] = useState("IPCA");
  const [sel, setSel] = useState<SerieIpea | null>(null);
  const [ultimos, setUltimos] = useState(48);

  const busca = useBalcao<NormalizedResponse<SerieIpea>>(caminho("ipeadata/series", { q, limite: 15 }));
  const series = busca.dados?.dados ?? [];

  // mantém uma seleção válida conforme a busca muda
  useEffect(() => {
    if (!series.length) {
      setSel(null);
      return;
    }
    setSel((atual) => (atual && series.some((s) => s.codigo === atual.codigo) ? atual : series[0]));
  }, [series]);

  const valores = useBalcao<NormalizedResponse<PontoIpea>>(
    sel ? caminho(`ipeadata/serie/${sel.codigo}`, { ultimos }) : null,
  );
  const pontos = (valores.dados?.dados ?? []).filter((p) => p.valor != null);
  const ultimo = pontos.at(-1);

  return (
    <div>
      <CadernoHeader
        numero="X"
        kicker="IPEADATA"
        titulo="O termômetro da economia"
        resumo="Milhares de séries macroeconômicas, regionais e sociais — PIB, inflação, emprego, renda — compiladas pelo Ipea. Busque pelo nome; a fonte despeja décadas de pontos e o Balcão recorta os recentes."
      />

      <form
        onSubmit={(e) => {
          e.preventDefault();
          setQ(texto.trim() || "IPCA");
        }}
        className="mb-5 flex flex-wrap items-center gap-2"
      >
        <input
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          placeholder="buscar série (ex: PIB, Selic, Desemprego)"
          className="w-72 rounded-md border border-line bg-surface px-3 py-1.5 text-ink placeholder:text-muted"
        />
        <button className="num rounded-md border border-accent bg-accent px-3 py-1.5 text-xs uppercase tracking-wider text-surface">
          buscar
        </button>
        <span className="mx-1 h-4 w-px bg-line" />
        {JANELAS.map((j) => (
          <button
            key={j}
            onClick={() => setUltimos(j)}
            aria-pressed={j === ultimos}
            className={`num rounded-md px-2 py-1 text-xs transition-colors ${
              j === ultimos ? "text-ink underline decoration-accent decoration-2 underline-offset-4" : "text-muted"
            }`}
          >
            {j} pts
          </button>
        ))}
      </form>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_1.3fr]">
        <div>
          <p className="kicker mb-3">
            {busca.carregando && !busca.dados ? "buscando…" : `${series.length} séries · "${q}"`}
          </p>
          {busca.erro ? (
            <ErroBox erro={busca.erro} aoTentar={busca.recarregar} />
          ) : busca.carregando && !busca.dados ? (
            <Esqueleto linhas={8} />
          ) : series.length === 0 ? (
            <Vazio>nenhuma série. A busca é pelo início do nome — tente “IPCA”, “PIB”, “Taxa”…</Vazio>
          ) : (
            <ul className="flex max-h-160 flex-col gap-1 overflow-y-auto pr-1">
              {series.map((s) => {
                const ativo = sel?.codigo === s.codigo;
                return (
                  <li key={s.codigo}>
                    <button
                      onClick={() => setSel(s)}
                      className={`flex w-full flex-col gap-0.5 rounded-md border px-3 py-2 text-left transition-colors ${
                        ativo ? "border-accent/40 bg-surface" : "border-transparent hover:bg-surface/70"
                      }`}
                    >
                      <span className="line-clamp-2 text-sm text-ink/90">{s.nome}</span>
                      <span className="num text-xs text-muted">
                        {[s.periodicidade, s.fonte_dados].filter(Boolean).join(" · ")}
                        {!s.ativa && " · descontinuada"}
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        <div>
          {!sel ? (
            <Vazio>escolha uma série.</Vazio>
          ) : (
            <Card className="overflow-hidden p-5 pt-6">
              <div className="mb-4 flex flex-wrap items-end justify-between gap-4 pl-5">
                {ultimo ? (
                  <Kpi
                    rotulo={`${sel.nome.slice(0, 28)} · último`}
                    valor={Number(ultimo.valor)}
                    formato="decimal"
                    sufixo={sel.unidade ?? undefined}
                    tom="accent-2"
                  />
                ) : (
                  <div className="h-12" />
                )}
                <div className="flex flex-col items-end gap-1.5">
                  <Carimbo
                    fonte="IPEADATA"
                    cache={valores.dados?.meta?.cache as string | undefined}
                    ms={valores.ms}
                    erro={!!valores.erro}
                  />
                  {ultimo && <span className="num text-xs text-muted">em {formataData(ultimo.data)}</span>}
                </div>
              </div>

              {valores.erro ? (
                <div className="px-5">
                  <ErroBox erro={valores.erro} aoTentar={valores.recarregar} />
                </div>
              ) : valores.carregando && !valores.dados ? (
                <div className="px-5">
                  <Esqueleto linhas={6} />
                </div>
              ) : pontos.length === 0 ? (
                <div className="px-5">
                  <Vazio>série sem pontos numéricos no período.</Vazio>
                </div>
              ) : (
                <SerieChart dados={pontos} cor="var(--color-accent-2)" />
              )}
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
