"use client";

import { useState } from "react";
import { CadernoHeader } from "@/components/Caderno";
import { Card } from "@/components/Card";
import { Carimbo } from "@/components/Carimbo";
import { SeloFonte } from "@/components/SeloFonte";
import { Esqueleto, ErroBox, Vazio, EmTransicao } from "@/components/Estados";
import { useBalcao } from "@/hooks/useBalcao";
import { caminho } from "@/lib/api";
import { UFS } from "@/lib/ufs";
import type { FonteDado, NormalizedResponse, PrecoCombustivel } from "@/lib/types";

const COMBUSTIVEIS = [
  ["gasolina", "Gasolina"],
  ["gasolina-aditivada", "Aditivada"],
  ["etanol", "Etanol"],
  ["diesel", "Diesel"],
  ["diesel-s10", "Diesel S10"],
  ["gnv", "GNV"],
  ["glp", "Botijão (GLP)"],
] as const;

const preco = (v: string) =>
  Number(v).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export default function CadernoCombustiveis() {
  const [combustivel, setCombustivel] = useState<string>("gasolina");
  const [por, setPor] = useState<"estado" | "municipio">("estado");
  const [uf, setUf] = useState("GO");

  const r = useBalcao<NormalizedResponse<PrecoCombustivel>>(
    caminho("anp/precos", {
      combustivel,
      por,
      uf: por === "municipio" ? uf : undefined,
      limit: por === "estado" ? 27 : 30,
    }),
  );
  const linhas = r.dados?.dados ?? [];
  const fonte = r.dados?.meta?.fonte as FonteDado | undefined;
  const de = r.dados?.meta?.coletas_de as string | undefined;
  const ate = r.dados?.meta?.coletas_ate as string | undefined;
  const min = linhas.length ? Number(linhas[0].preco_medio) : 0;
  const max = linhas.length ? Number(linhas[linhas.length - 1].preco_medio) : 1;
  const unidade = linhas[0]?.unidade ?? "R$ / litro";

  return (
    <div>
      <CadernoHeader
        numero="XXI"
        kicker="ANP · pesquisa semanal"
        titulo="Combustíveis"
        resumo="Quanto tá a gasolina — e o etanol, o diesel e o botijão — em cada estado e cidade, na média real das coletas da ANP nos postos nas últimas quatro semanas. Do mais barato pro mais caro."
      />

      <div className="mb-5 flex flex-wrap items-center gap-3">
        <div className="flex flex-wrap items-center gap-2">
          {COMBUSTIVEIS.map(([v, label]) => (
            <button
              key={v}
              onClick={() => setCombustivel(v)}
              aria-pressed={combustivel === v}
              className={`num rounded-full border px-3 py-1 text-xs uppercase tracking-wider transition-colors ${
                combustivel === v
                  ? "border-accent bg-accent text-surface"
                  : "border-line text-muted hover:border-accent hover:text-accent"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        <span className="mx-1 h-4 w-px bg-line" />
        <div className="inline-flex gap-0.5 rounded-md border border-line p-0.5">
          {(
            [
              ["estado", "Estados"],
              ["municipio", "Cidades"],
            ] as const
          ).map(([v, label]) => (
            <button
              key={v}
              onClick={() => setPor(v)}
              aria-pressed={por === v}
              className={`num rounded px-3 py-1 text-xs uppercase tracking-wider transition-colors ${
                por === v ? "bg-accent/15 font-semibold text-accent" : "text-muted hover:text-ink"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        {por === "municipio" && (
          <select
            value={uf}
            onChange={(e) => setUf(e.target.value)}
            className="rounded-md border border-line bg-surface px-2 py-1.5 text-sm text-ink focus:border-accent focus:outline-none"
            aria-label="estado"
          >
            {UFS.map((u) => (
              <option key={u}>{u}</option>
            ))}
          </select>
        )}
        <Carimbo fonte="ANP" cache={r.dados?.meta?.cache as string | undefined} ms={r.ms} erro={!!r.erro} />
      </div>

      {de && ate && (
        <p className="kicker mb-3">
          coletas de <span className="num text-ink">{de}</span> a <span className="num text-ink">{ate}</span> · {unidade}
        </p>
      )}

      {r.erro ? (
        <ErroBox erro={r.erro} aoTentar={r.recarregar} />
      ) : r.carregando && !r.dados ? (
        <Esqueleto linhas={10} />
      ) : linhas.length ? (
        <EmTransicao ativo={r.carregando}>
          <Card className="p-5 sm:p-6">
            <ol className="flex flex-col gap-3">
              {linhas.map((l, i) => {
                const v = Number(l.preco_medio);
                // do verde (mais barato) ao vermelho (mais caro)
                const t = max > min ? (v - min) / (max - min) : 0;
                const cor = `hsl(${Math.round(140 - 140 * t)} 62% 42%)`;
                return (
                  <li key={l.local} className="flex items-center gap-3">
                    <span className="num w-6 shrink-0 text-right text-sm text-muted">{i + 1}</span>
                    <div className="min-w-0 flex-1">
                      <div className="mb-1 flex items-baseline justify-between gap-3">
                        <span className="truncate text-sm text-ink/90" title={l.local}>
                          {l.local}
                          {por === "municipio" && <span className="num ml-1.5 text-xs text-muted">{l.uf}</span>}
                        </span>
                        <span className="num shrink-0 text-sm text-ink">
                          R$ {preco(l.preco_medio)}
                          <span className="ml-1.5 text-xs text-muted">
                            {preco(l.preco_minimo)}–{preco(l.preco_maximo)}
                          </span>
                        </span>
                      </div>
                      <div className="h-2 overflow-hidden rounded-sm bg-surface-2">
                        <div
                          className="h-full rounded-sm transition-all duration-500"
                          style={{ width: `${Math.max((100 * v) / max, 2)}%`, background: cor }}
                        />
                      </div>
                    </div>
                  </li>
                );
              })}
            </ol>
            <p className="mt-5 border-t border-line pt-3 font-editorial text-sm italic text-muted">
              Média simples das coletas nos postos ({linhas.reduce((s, l) => s + l.coletas, 0).toLocaleString("pt-BR")}{" "}
              no recorte). O preço do seu posto pode variar — a faixa mín–máx dá a dimensão.
            </p>
          </Card>
        </EmTransicao>
      ) : (
        <Vazio>sem coletas pra esse recorte nas últimas semanas.</Vazio>
      )}

      <SeloFonte fonte={fonte} />
    </div>
  );
}
