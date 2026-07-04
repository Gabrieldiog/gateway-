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
import { CAPITAIS, UFS } from "@/lib/ufs";
import type { AlertaDengue, FonteDado, Municipio, NormalizedResponse } from "@/lib/types";

const DOENCAS = [
  ["dengue", "Dengue"],
  ["zika", "Zika"],
  ["chikungunya", "Chikungunya"],
] as const;

// as cores do semáforo do InfoDengue
const COR_ALERTA: Record<string, { texto: string; fundo: string; barra: string }> = {
  verde: { texto: "text-emerald-600", fundo: "bg-emerald-500/10", barra: "#10b981" },
  amarelo: { texto: "text-amber-600", fundo: "bg-amber-400/10", barra: "#f59e0b" },
  laranja: { texto: "text-orange-600", fundo: "bg-orange-500/10", barra: "#f97316" },
  vermelho: { texto: "text-rose-600", fundo: "bg-rose-600/10", barra: "#e11d48" },
};

const inteiro = (v: number | null) =>
  v == null ? "—" : Math.round(v).toLocaleString("pt-BR");

export default function CadernoDengue() {
  const [uf, setUf] = useState("GO");
  const [ibge, setIbge] = useState(CAPITAIS.GO);
  const [doenca, setDoenca] = useState<string>("dengue");

  const cidades = useBalcao<NormalizedResponse<Municipio>>(caminho("ibge/municipios", { uf }));
  const r = useBalcao<NormalizedResponse<AlertaDengue>>(
    caminho("infodengue/alertas", { municipio: ibge, doenca }),
  );

  const semanas = r.dados?.dados ?? [];
  const atual = semanas[0];
  const fonte = r.dados?.meta?.fonte as FonteDado | undefined;
  const cor = atual ? (COR_ALERTA[atual.alerta] ?? COR_ALERTA.verde) : COR_ALERTA.verde;
  // as barras da série (mais antiga -> mais recente) pra ler a tendência
  const serie = [...semanas].reverse();
  const maxEst = Math.max(...serie.map((s) => s.casos_estimados ?? 0), 1);

  return (
    <div>
      <CadernoHeader
        numero="XIX"
        kicker="InfoDengue · Fiocruz"
        titulo="Dengue"
        resumo="O alerta de arboviroses da sua cidade, semana a semana: casos notificados, a estimativa corrigida do modelo da Fiocruz e o semáforo de verde a vermelho. Escolha a cidade e a doença."
      />

      <div className="mb-5 flex flex-wrap items-center gap-3">
        <Seletor value={uf} onChange={(e) => { setUf(e.target.value); setIbge(CAPITAIS[e.target.value]); }} aria-label="estado">
          {UFS.map((u) => (
            <option key={u}>{u}</option>
          ))}
        </Seletor>
        <Seletor value={ibge} onChange={(e) => setIbge(e.target.value)} className="max-w-56" aria-label="cidade">
          {(cidades.dados?.dados ?? []).map((m) => (
            <option key={m.id} value={String(m.id)}>
              {m.nome}
            </option>
          ))}
        </Seletor>
        <div className="inline-flex gap-0.5 rounded-md border border-line p-0.5">
          {DOENCAS.map(([v, label]) => (
            <button
              key={v}
              onClick={() => setDoenca(v)}
              aria-pressed={doenca === v}
              className={`num rounded px-2.5 py-1 text-xs uppercase tracking-wider transition-colors ${
                doenca === v ? "bg-accent/15 font-semibold text-accent" : "text-muted hover:text-ink"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        <Carimbo fonte="FIOCRUZ" cache={r.dados?.meta?.cache as string | undefined} ms={r.ms} erro={!!r.erro} />
      </div>

      {r.erro ? (
        <ErroBox erro={r.erro} aoTentar={r.recarregar} />
      ) : r.carregando && !r.dados ? (
        <Esqueleto linhas={6} />
      ) : atual ? (
        <EmTransicao ativo={r.carregando}>
          <Card className={`p-6 ${cor.fundo}`}>
            <div className="flex flex-wrap items-end justify-between gap-6 pl-4">
              <div>
                <p className="kicker mb-2">
                  {atual.municipio} · semana de {formataData(atual.inicio_semana)}
                </p>
                <p className={`font-display text-4xl sm:text-5xl font-semibold uppercase leading-none tracking-tight ${cor.texto}`}>
                  {atual.alerta}
                </p>
              </div>
              <div className="flex flex-wrap gap-x-10 gap-y-3">
                <div>
                  <p className="kicker mb-1">casos estimados</p>
                  <p className="num text-3xl font-semibold text-ink">{inteiro(atual.casos_estimados)}</p>
                </div>
                <div>
                  <p className="kicker mb-1">notificados</p>
                  <p className="num text-3xl font-semibold text-ink">{inteiro(atual.casos)}</p>
                </div>
                <div>
                  <p className="kicker mb-1">
                    <Termo t="rt">Rt</Termo>
                  </p>
                  <p className={`num text-3xl font-semibold ${(atual.rt ?? 0) > 1 ? "text-rose-600" : "text-ink"}`}>
                    {atual.rt?.toFixed(2) ?? "—"}
                  </p>
                </div>
              </div>
            </div>
          </Card>

          <Card className="mt-5 p-5 pt-6">
            <p className="kicker mb-4 pl-4">as últimas {serie.length} semanas · casos estimados</p>
            <div className="flex h-36 items-end gap-1 pl-4">
              {serie.map((s) => {
                const c = COR_ALERTA[s.alerta] ?? COR_ALERTA.verde;
                const h = Math.max((100 * (s.casos_estimados ?? 0)) / maxEst, 2);
                return (
                  <div
                    key={s.semana}
                    className="min-w-0 flex-1 rounded-t-sm transition-all duration-500"
                    style={{ height: `${h}%`, background: c.barra }}
                    title={`SE ${s.semana}: ${inteiro(s.casos_estimados)} estimados (${s.alerta})`}
                  />
                );
              })}
            </div>
            <p className="mt-4 border-t border-line pt-3 font-editorial text-sm italic text-muted">
              As semanas recentes são estimativa (<Termo t="nowcast">nowcast</Termo>) — o modelo
              corrige o atraso de notificação, então os números se ajustam a cada atualização.
            </p>
          </Card>
        </EmTransicao>
      ) : (
        <Vazio>sem dados pra essa cidade/doença neste ano.</Vazio>
      )}

      <SeloFonte fonte={fonte} />
    </div>
  );
}
