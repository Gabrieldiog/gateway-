"use client";

import { useEffect, useState } from "react";
import { CadernoHeader } from "@/components/Caderno";
import { Card } from "@/components/Card";
import { BadgeAoVivo } from "@/components/Frescor";
import { SeloFonte } from "@/components/SeloFonte";
import { Termo } from "@/components/Termo";
import { Esqueleto, ErroBox } from "@/components/Estados";
import { useBalcao } from "@/hooks/useBalcao";
import { useTicker } from "@/hooks/useTicker";
import { caminho } from "@/lib/api";
import type { FonteDado, GeracaoEnergia, NormalizedResponse } from "@/lib/types";

const INTERVALO = 30000; // 30s — o ONS publica um novo minuto a cada ~60s

// ordem fixa (não reordena a cada poll) + cor por fonte
const FONTES: {
  nome: string;
  cor: string;
  renovavel: boolean;
  get: (g: GeracaoEnergia) => number;
}[] = [
  { nome: "Hidráulica", cor: "var(--color-accent-2)", renovavel: true, get: (g) => g.hidraulica },
  { nome: "Eólica", cor: "#10b981", renovavel: true, get: (g) => g.eolica },
  { nome: "Solar", cor: "#f59e0b", renovavel: true, get: (g) => g.solar },
  { nome: "Térmica", cor: "#f43f5e", renovavel: false, get: (g) => g.termica },
  { nome: "Nuclear", cor: "#8b5cf6", renovavel: false, get: (g) => g.nuclear },
];

const mw = (v: number) => Math.round(v).toLocaleString("pt-BR");
const pct = (v: number) => v.toLocaleString("pt-BR", { maximumFractionDigits: 1 });

function horaDe(instante: string): string {
  return instante.match(/T(\d{2}:\d{2})/)?.[1] ?? "—";
}

function Telao({ sin }: { sin: GeracaoEnergia }) {
  const geracao = useTicker(sin.geracao_total);
  const renov = useTicker(sin.renovavel_pct ?? 0);
  return (
    <Card className="overflow-hidden p-6 sm:p-8">
      <div className="flex flex-wrap items-end justify-between gap-6">
        <div>
          <p className="kicker mb-2 text-accent">o Brasil está gerando agora</p>
          <p className="num tabular-nums font-display text-5xl font-semibold leading-none tracking-tight text-ink sm:text-7xl">
            {mw(geracao)}
            <span className="ml-2 align-baseline text-2xl font-normal text-muted sm:text-3xl">MW</span>
          </p>
        </div>
        <div className="flex flex-col items-end">
          <span className="kicker mb-1 text-emerald-500">renovável</span>
          <span className="num tabular-nums font-display text-4xl font-semibold leading-none tracking-tight text-emerald-500 sm:text-5xl">
            {pct(renov)}
            <span className="text-xl">%</span>
          </span>
        </div>
      </div>

      {/* barra única de composição: renovável vs não-renovável */}
      <div className="mt-6 flex h-3 overflow-hidden rounded-full bg-surface-2">
        {FONTES.map((f) => {
          const p = sin.geracao_total ? (100 * f.get(sin)) / sin.geracao_total : 0;
          return (
            <div
              key={f.nome}
              className="h-full transition-all duration-700"
              style={{ width: `${p}%`, background: f.cor }}
              title={`${f.nome}: ${pct(p)}%`}
            />
          );
        })}
      </div>
    </Card>
  );
}

function MixFontes({ sin }: { sin: GeracaoEnergia }) {
  return (
    <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {FONTES.map((f) => {
        const valor = f.get(sin);
        const p = sin.geracao_total ? (100 * valor) / sin.geracao_total : 0;
        return (
          <Card key={f.nome} className="p-4 pt-5">
            <div className="flex items-center justify-between pl-4">
              <span className="flex items-center gap-2 text-sm font-semibold text-ink">
                <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: f.cor }} />
                {f.nome}
                {f.renovavel && (
                  <span className="num text-[0.6rem] uppercase tracking-wider text-emerald-500">renov.</span>
                )}
              </span>
              <span className="num tabular-nums text-sm text-muted">{pct(p)}%</span>
            </div>
            <p className="num tabular-nums mt-2 pl-4 text-2xl font-semibold tracking-tight text-ink">
              {mw(valor)} <span className="text-sm font-normal text-muted">MW</span>
            </p>
            <div className="mt-2 ml-4 h-1.5 rounded-full bg-surface-2">
              <div
                className="h-1.5 rounded-full transition-all duration-700"
                style={{ width: `${p}%`, background: f.cor }}
              />
            </div>
          </Card>
        );
      })}
    </div>
  );
}

function Subsistemas({ regioes }: { regioes: GeracaoEnergia[] }) {
  return (
    <div className="mt-6">
      <p className="kicker mb-3">
        por subsistema do <Termo t="sin">SIN</Termo>
      </p>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {regioes.map((r) => (
          <Card key={r.regiao} className="p-4 pt-5">
            <p className="kicker mb-2 pl-4">{r.regiao}</p>
            <p className="num tabular-nums pl-4 text-xl font-semibold tracking-tight text-ink">
              {mw(r.geracao_total)} <span className="text-xs font-normal text-muted">MW</span>
            </p>
            <p className="num mt-1 pl-4 text-xs text-emerald-500">
              {pct(r.renovavel_pct ?? 0)}% renovável
            </p>
          </Card>
        ))}
      </div>
    </div>
  );
}

export default function CadernoEnergia() {
  const energia = useBalcao<NormalizedResponse<GeracaoEnergia>>(caminho("ons/geracao"));
  const { recarregar } = energia;

  // polling: refaz sozinho pra o número acompanhar a geração ao vivo
  useEffect(() => {
    const id = setInterval(() => recarregar(), INTERVALO);
    return () => clearInterval(id);
  }, [recarregar]);

  const dados = energia.dados?.dados ?? [];
  const sin = dados.find((d) => d.regiao === "SIN") ?? dados[0];
  const regioes = dados.filter((d) => d.regiao !== "SIN");
  const fonte = energia.dados?.meta?.fonte as FonteDado | undefined;
  const instante = (energia.dados?.meta?.instante as string | undefined) ?? sin?.instante;

  // transparência do ao-vivo: a hora de cada resposta nova, visível no selo
  const [atualizadoEm, setAtualizadoEm] = useState<number | null>(null);
  useEffect(() => {
    if (energia.dados) setAtualizadoEm(Date.now());
  }, [energia.dados]);

  return (
    <div>
      <CadernoHeader
        numero="XV"
        kicker="ONS · tempo real"
        titulo="Energia ao vivo"
        resumo="Quanto o Brasil está gerando de energia neste minuto, e de onde ela vem. O Sistema Interligado Nacional atualiza a cada minuto — a página acompanha e o número desliza pro novo valor. Dado real do ONS, não estimativa."
      />

      <div className="mb-5 flex flex-wrap items-center gap-3">
        <BadgeAoVivo atualizadoEm={atualizadoEm} />
        <span className="num text-xs uppercase tracking-wider text-muted">
          a cada 30s, sozinho
          {instante && <span className="text-ink"> · leitura do ONS das {horaDe(instante)}</span>}
        </span>
      </div>

      {energia.erro ? (
        <ErroBox erro={energia.erro} aoTentar={recarregar} />
      ) : !sin ? (
        <Esqueleto linhas={6} />
      ) : (
        <>
          <Telao sin={sin} />
          <MixFontes sin={sin} />
          {regioes.length > 0 && <Subsistemas regioes={regioes} />}
          <SeloFonte fonte={fonte} />
        </>
      )}
    </div>
  );
}
