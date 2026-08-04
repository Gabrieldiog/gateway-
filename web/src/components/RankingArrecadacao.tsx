"use client";

import { useState } from "react";
import { Card } from "@/components/Card";
import { Carimbo } from "@/components/Carimbo";
import { Seletor } from "@/components/Seletor";
import { Esqueleto, ErroBox, Vazio, EmTransicao } from "@/components/Estados";
import { useBalcao } from "@/hooks/useBalcao";
import { caminho, formataBRL, formataReaisCompacto } from "@/lib/api";
import type { Ranking } from "@/lib/types";

type Nivel = "estado" | "capital";
type Criterio = { label: string; por?: "per_capita"; imposto?: string };

// os critérios mudam por nível: estado tem ICMS/IPVA; cidade tem ISS/IPTU
const CRITERIOS: Record<Nivel, Criterio[]> = {
  estado: [
    { label: "Total" },
    { label: "Per capita", por: "per_capita" },
    { label: "ICMS", imposto: "ICMS" },
    { label: "IPVA", imposto: "IPVA" },
    { label: "ITCMD", imposto: "ITCMD" },
    { label: "IR", imposto: "IR" },
  ],
  capital: [
    { label: "Total" },
    { label: "Per capita", por: "per_capita" },
    { label: "ISS", imposto: "ISS" },
    { label: "IPTU", imposto: "IPTU" },
    { label: "ITBI", imposto: "ITBI" },
    { label: "IR", imposto: "IR" },
  ],
};

export function RankingArrecadacao({ ano }: { ano: number }) {
  const [nivel, setNivel] = useState<Nivel>("estado");
  const [idx, setIdx] = useState(0);
  const criterios = CRITERIOS[nivel];
  const criterio = criterios[idx] ?? criterios[0];
  const perCapita = criterio.por === "per_capita";

  const r = useBalcao<Ranking>(
    caminho("arrecadacao/ranking", { nivel, ano, por: criterio.por, imposto: criterio.imposto }),
  );
  const linhas = r.dados?.ranking ?? [];
  const max = linhas.length ? Number(linhas[0].valor) : 1;

  function trocaNivel(n: Nivel) {
    setNivel(n);
    setIdx(0);
  }

  const fmt = (v: string) => (perCapita ? `${formataBRL(Number(v))} / hab` : formataReaisCompacto(v));
  const oQue = perCapita ? "imposto por habitante" : criterio.imposto ?? "total de impostos";

  return (
    <div>
      <div className="mb-5 flex flex-wrap items-center gap-x-5 gap-y-3">
        <div className="inline-flex gap-0.5 rounded-md border border-line p-0.5">
          {(
            [
              ["estado", "Estados"],
              ["capital", "Capitais"],
            ] as [Nivel, string][]
          ).map(([v, label]) => (
            <button
              key={v}
              onClick={() => trocaNivel(v)}
              aria-pressed={nivel === v}
              className={`num rounded px-3 py-1 text-xs uppercase tracking-wider transition-colors ${
                nivel === v ? "bg-accent/15 font-semibold text-accent" : "text-muted hover:text-ink"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        <label className="num flex items-center gap-2 text-xs uppercase tracking-wider text-muted">
          Critério
          <Seletor value={idx} onChange={(e) => setIdx(Number(e.target.value))}>
            {criterios.map((c, i) => (
              <option key={c.label} value={i}>
                {c.label}
              </option>
            ))}
          </Seletor>
        </label>
      </div>

      <p className="kicker mb-3 flex items-center justify-between">
        <span>
          {nivel === "estado" ? "Estados" : "Capitais"} por {oQue} · {ano}
        </span>
        <Carimbo fonte="TESOURO" ms={r.ms} erro={!!r.erro} />
      </p>

      {r.erro ? (
        <ErroBox erro={r.erro} aoTentar={r.recarregar} />
      ) : r.carregando && !r.dados ? (
        <Esqueleto linhas={8} />
      ) : linhas.length ? (
        <EmTransicao ativo={r.carregando}>
          <Card className="p-5 sm:p-6">
            <ol className="flex flex-col gap-3">
              {linhas.map((l, i) => (
                <li key={`${l.uf}-${l.ente}`} className="flex items-center gap-3">
                  <span className="num w-6 shrink-0 text-right text-sm text-muted">{i + 1}</span>
                  <div className="min-w-0 flex-1">
                    <div className="mb-1 flex items-baseline justify-between gap-3">
                      <span className="truncate text-sm text-ink/90" title={l.ente}>
                        {l.ente}
                        {nivel === "capital" && (
                          <span className="num ml-1.5 text-xs text-muted">{l.uf}</span>
                        )}
                      </span>
                      <span className={`num shrink-0 text-sm ${i === 0 ? "text-accent" : "text-ink"}`}>
                        {fmt(l.valor)}
                      </span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-sm bg-surface-2">
                      <div
                        className={`h-full rounded-sm ${i === 0 ? "bg-accent" : "bg-ink/70"}`}
                        style={{ width: `${Math.max((Number(l.valor) / max) * 100, 1.5)}%` }}
                      />
                    </div>
                  </div>
                </li>
              ))}
            </ol>
            <p className="mt-5 border-t border-line pt-3 font-editorial text-sm italic text-muted">
              {r.dados?.total_entes ?? linhas.length}{" "}
              {nivel === "estado" ? "estados" : "capitais"} com contas declaradas em {ano}.
              {nivel === "capital" && " Ranking entre as capitais, não inclui as demais cidades."}
            </p>
          </Card>
        </EmTransicao>
      ) : (
        <Vazio>sem dados de ranking para {ano}.</Vazio>
      )}
    </div>
  );
}
