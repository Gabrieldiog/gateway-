"use client";

import { useState } from "react";
import { CadernoHeader } from "@/components/Caderno";
import { Card } from "@/components/Card";
import { Carimbo } from "@/components/Carimbo";
import { SeloFonte } from "@/components/SeloFonte";
import { Seletor } from "@/components/Seletor";
import { Termo } from "@/components/Termo";
import { Esqueleto, ErroBox, Vazio, EmTransicao } from "@/components/Estados";
import { useBalcao } from "@/hooks/useBalcao";
import { caminho, formataData } from "@/lib/api";
import type { AlertaDesmatamento, FonteDado, NormalizedResponse } from "@/lib/types";

const BIOMAS: [string, string][] = [
  ["amazonia", "Amazônia"],
  ["cerrado", "Cerrado"],
];

const NIVEIS: [string, string][] = [
  ["uf", "por estado"],
  ["classe", "por tipo"],
  ["municipio", "por município"],
];

function km2(v: number): string {
  return `${v.toLocaleString("pt-BR", { maximumFractionDigits: 1 })} km²`;
}

export default function CadernoDesmatamento() {
  const [bioma, setBioma] = useState("amazonia");
  const [dias, setDias] = useState("30");
  const [nivel, setNivel] = useState("uf");

  const r = useBalcao<NormalizedResponse<AlertaDesmatamento>>(
    caminho("inpe/desmatamento", { bioma, dias, por: nivel, limit: 15 }),
  );
  const itens = r.dados?.dados ?? [];
  const maior = itens[0]?.area_km2 ?? 0;
  const totalAlertas = r.dados?.meta?.alertas_total as number | undefined;
  const areaTotal = r.dados?.meta?.area_total_km2 as number | undefined;
  const ultima = r.dados?.meta?.ultima_deteccao as string | null | undefined;
  const fonte = r.dados?.meta?.fonte as FonteDado | undefined;

  return (
    <div>
      <CadernoHeader
        numero="XXXV"
        kicker="INPE · TerraBrasilis"
        titulo="Desmatamento"
        resumo="Onde a floresta caiu nas últimas semanas, segundo os satélites do INPE. Alerta é o aviso quente — serve pra fiscalização chegar; a taxa oficial do ano (PRODES) é outra conta, mais lenta e completa."
      />

      <div className="mb-6 flex flex-wrap items-center gap-3">
        <div className="flex flex-wrap gap-0.5 rounded-md border border-line p-0.5">
          {BIOMAS.map(([v, label]) => (
            <button
              key={v}
              onClick={() => setBioma(v)}
              aria-pressed={bioma === v}
              className={`num rounded px-3 py-1 text-xs uppercase tracking-wider transition-colors ${
                bioma === v ? "bg-accent/15 font-semibold text-accent" : "text-muted hover:text-ink"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        <Seletor value={dias} onChange={(e) => setDias(e.target.value)} aria-label="janela">
          <option value="30">últimos 30 dias</option>
          <option value="60">últimos 60 dias</option>
          <option value="90">últimos 90 dias</option>
        </Seletor>
        <Carimbo fonte="INPE" cache={r.dados?.meta?.cache as string | undefined} ms={r.ms} erro={!!r.erro} />
      </div>

      {r.erro ? (
        <ErroBox erro={r.erro} aoTentar={r.recarregar} />
      ) : r.carregando && !r.dados ? (
        <Esqueleto linhas={8} />
      ) : (
        <EmTransicao ativo={r.carregando}>
          <div className="mb-6 grid gap-3 sm:grid-cols-3">
            <Card className="p-4">
              <p className="kicker">alertas na janela</p>
              <p className="num mt-1 text-3xl font-semibold text-erro">
                {totalAlertas?.toLocaleString("pt-BR") ?? "—"}
              </p>
            </Card>
            <Card className="p-4">
              <p className="kicker">área com alerta</p>
              <p className="num mt-1 text-3xl font-semibold text-ink">
                {areaTotal != null ? km2(areaTotal) : "—"}
              </p>
            </Card>
            <Card className="p-4">
              <p className="kicker">última detecção</p>
              <p className="num mt-1 text-3xl font-semibold text-ink">
                {ultima ? formataData(ultima) : "—"}
              </p>
            </Card>
          </div>

          <div className="mb-4 flex flex-wrap items-center gap-3">
            <div className="flex flex-wrap gap-0.5 rounded-md border border-line p-0.5">
              {NIVEIS.map(([v, label]) => (
                <button
                  key={v}
                  onClick={() => setNivel(v)}
                  aria-pressed={nivel === v}
                  className={`num rounded px-3 py-1 text-xs uppercase tracking-wider transition-colors ${
                    nivel === v ? "bg-accent/15 font-semibold text-accent" : "text-muted hover:text-ink"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
          <p className="mb-4 max-w-2xl font-editorial text-sm leading-relaxed text-ink/75">
            Cada linha soma os alertas do <Termo t="deter">DETER</Termo> na janela — do{" "}
            <Termo t="corteraso">corte raso</Termo> à mineração. Nuvem esconde: o número é piso,
            não teto.
          </p>

          {itens.length ? (
            <Card className="p-5">
              <ul className="flex flex-col gap-2.5">
                {itens.map((i) => (
                  <li key={i.nome}>
                    <div className="flex items-baseline justify-between gap-3">
                      <span className="min-w-0 flex-1 truncate text-sm text-ink">{i.nome}</span>
                      <span className="num shrink-0 text-xs text-muted">
                        {i.alertas.toLocaleString("pt-BR")} alertas
                      </span>
                      <span className="num w-24 shrink-0 text-right text-sm font-semibold text-ink">
                        {km2(i.area_km2)}
                      </span>
                    </div>
                    <div className="mt-0.5 h-1.5 overflow-hidden rounded-full bg-surface-2">
                      <div
                        className="h-full rounded-full bg-erro/70"
                        style={{ width: `${maior ? Math.max(2, (i.area_km2 / maior) * 100) : 0}%` }}
                      />
                    </div>
                  </li>
                ))}
              </ul>
            </Card>
          ) : (
            <Vazio>nenhum alerta na janela — bom sinal (ou muita nuvem).</Vazio>
          )}
        </EmTransicao>
      )}

      <SeloFonte fonte={fonte} />
    </div>
  );
}
