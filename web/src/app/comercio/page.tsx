"use client";

import { useState } from "react";
import { CadernoHeader } from "@/components/Caderno";
import { Card } from "@/components/Card";
import { Carimbo } from "@/components/Carimbo";
import { BadgeFrescor } from "@/components/Frescor";
import { SeloFonte } from "@/components/SeloFonte";
import { Esqueleto, ErroBox, Vazio, EmTransicao } from "@/components/Estados";
import { useBalcao } from "@/hooks/useBalcao";
import { caminho } from "@/lib/api";
import type { BalancaMensal, FonteDado, LinhaComercio, NormalizedResponse } from "@/lib/types";

type Dim = "pais" | "uf" | "produto";
type Fluxo = "exportacao" | "importacao";

const DIMS: [Dim, string][] = [
  ["pais", "Países"],
  ["uf", "Estados"],
  ["produto", "Produtos"],
];

const MES_NOME = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];

// US$ em escala curta: 46,3 bi · 890 mi
function usd(valor: string | number): string {
  const n = typeof valor === "string" ? Number(valor) : valor;
  const abs = Math.abs(n);
  if (abs >= 1e9) return `US$ ${(n / 1e9).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} bi`;
  if (abs >= 1e6) return `US$ ${(n / 1e6).toLocaleString("pt-BR", { maximumFractionDigits: 0 })} mi`;
  return `US$ ${n.toLocaleString("pt-BR", { maximumFractionDigits: 0 })}`;
}

function rotuloMes(mes: string): string {
  const m = Number(mes.split("-")[1]);
  return MES_NOME[m - 1] ?? mes;
}

function Balanca() {
  const r = useBalcao<NormalizedResponse<BalancaMensal>>(caminho("comex/balanca"));
  const meses = r.dados?.dados ?? [];
  const totalExp = meses.reduce((s, m) => s + Number(m.exportacoes), 0);
  const totalImp = meses.reduce((s, m) => s + Number(m.importacoes), 0);
  const maxBarra = Math.max(...meses.map((m) => Math.max(Number(m.exportacoes), Number(m.importacoes))), 1);

  return (
    <section>
      <p className="kicker mb-3 flex items-center justify-between">
        <span>balança comercial · {new Date().getFullYear()}</span>
        <Carimbo fonte="MDIC" cache={r.dados?.meta?.cache as string | undefined} ms={r.ms} erro={!!r.erro} />
      </p>
      {r.erro ? (
        <ErroBox erro={r.erro} aoTentar={r.recarregar} />
      ) : r.carregando && !r.dados ? (
        <Esqueleto linhas={6} />
      ) : meses.length ? (
        <EmTransicao ativo={r.carregando}>
          <Card className="p-6">
            <div className="flex flex-wrap gap-x-12 gap-y-4 pl-4">
              <div>
                <p className="kicker mb-1">exportações</p>
                <p className="num text-3xl font-semibold text-emerald-600">{usd(totalExp)}</p>
              </div>
              <div>
                <p className="kicker mb-1">importações</p>
                <p className="num text-3xl font-semibold text-rose-600">{usd(totalImp)}</p>
              </div>
              <div>
                <p className="kicker mb-1">saldo</p>
                <p className={`num text-3xl font-semibold ${totalExp - totalImp >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                  {totalExp - totalImp >= 0 ? "+" : ""}
                  {usd(totalExp - totalImp)}
                </p>
              </div>
            </div>

            <div className="mt-6 flex flex-col gap-3 pl-4">
              {meses.map((m) => {
                const saldo = Number(m.saldo);
                return (
                  <div key={m.mes} className="flex items-center gap-3">
                    <span className="num w-8 shrink-0 text-right text-xs uppercase text-muted">{rotuloMes(m.mes)}</span>
                    <div className="min-w-0 flex-1">
                      <div className="flex h-2.5 overflow-hidden rounded-sm bg-surface-2">
                        <div className="h-full bg-emerald-500" style={{ width: `${(100 * Number(m.exportacoes)) / maxBarra}%` }} title={`exportações ${usd(m.exportacoes)}`} />
                      </div>
                      <div className="mt-0.5 flex h-2.5 overflow-hidden rounded-sm bg-surface-2">
                        <div className="h-full bg-rose-400" style={{ width: `${(100 * Number(m.importacoes)) / maxBarra}%` }} title={`importações ${usd(m.importacoes)}`} />
                      </div>
                    </div>
                    <span className={`num w-24 shrink-0 text-right text-xs ${saldo >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                      {saldo >= 0 ? "+" : ""}
                      {usd(saldo)}
                    </span>
                  </div>
                );
              })}
            </div>
            <p className="mt-5 border-t border-line pt-3 font-editorial text-sm italic text-muted">
              Verde: exportações · rosa: importações. Valores em dólares FOB, fechados mês a mês pela
              Secretaria de Comércio Exterior.
            </p>
          </Card>
        </EmTransicao>
      ) : (
        <Vazio>sem dados fechados pra este ano ainda.</Vazio>
      )}
    </section>
  );
}

function ListaDestaque({
  titulo,
  tom,
  linhas,
  carregando,
}: {
  titulo: string;
  tom: "verde" | "rosa";
  linhas: LinhaComercio[];
  carregando: boolean;
}) {
  const cor = tom === "verde" ? "text-emerald-600" : "text-rose-600";
  const barra = tom === "verde" ? "bg-emerald-500" : "bg-rose-400";
  const max = linhas.length ? Number(linhas[0].valor_fob) : 1;
  return (
    <Card className="p-5 pt-6">
      <p className={`kicker mb-3 pl-4 ${cor}`}>{titulo}</p>
      {carregando && !linhas.length ? (
        <Esqueleto linhas={5} />
      ) : (
        <ol className="flex flex-col gap-2.5 pl-4">
          {linhas.map((l, i) => (
            <li key={l.nome}>
              <div className="mb-0.5 flex items-baseline justify-between gap-3">
                <span className="num w-4 shrink-0 text-xs text-muted">{i + 1}</span>
                <span className="min-w-0 flex-1 truncate text-sm text-ink/90" title={l.nome}>
                  {l.nome}
                </span>
                <span className="num shrink-0 text-sm text-ink">{usd(l.valor_fob)}</span>
              </div>
              <div className="ml-6 h-1.5 overflow-hidden rounded-sm bg-surface-2">
                <div
                  className={`h-full rounded-sm ${barra}`}
                  style={{ width: `${Math.max((100 * Number(l.valor_fob)) / max, 2)}%` }}
                />
              </div>
            </li>
          ))}
        </ol>
      )}
    </Card>
  );
}

function Destaques() {
  // as duas perguntas mais diretas do caderno, sempre à vista
  const vende = useBalcao<NormalizedResponse<LinhaComercio>>(
    caminho("comex/ranking/produto", { fluxo: "exportacao", limit: 5 }),
  );
  const compra = useBalcao<NormalizedResponse<LinhaComercio>>(
    caminho("comex/ranking/produto", { fluxo: "importacao", limit: 5 }),
  );
  if (vende.erro && compra.erro) return null;
  return (
    <section className="mt-10">
      <p className="kicker mb-3">o que o Brasil mais vende · e mais compra</p>
      <div className="grid gap-4 lg:grid-cols-2">
        <ListaDestaque
          titulo="mais vende (exportação)"
          tom="verde"
          linhas={vende.dados?.dados ?? []}
          carregando={vende.carregando}
        />
        <ListaDestaque
          titulo="mais compra (importação)"
          tom="rosa"
          linhas={compra.dados?.dados ?? []}
          carregando={compra.carregando}
        />
      </div>
    </section>
  );
}

function Rankings() {
  const [dim, setDim] = useState<Dim>("pais");
  const [fluxo, setFluxo] = useState<Fluxo>("exportacao");

  const r = useBalcao<NormalizedResponse<LinhaComercio>>(
    caminho(`comex/ranking/${dim}`, { fluxo, limit: 12 }),
  );
  const linhas = r.dados?.dados ?? [];
  const max = linhas.length ? Number(linhas[0].valor_fob) : 1;
  const fonte = r.dados?.meta?.fonte as FonteDado | undefined;

  return (
    <section className="mt-10">
      <div className="mb-4 flex flex-wrap items-center gap-4">
        <div className="inline-flex gap-0.5 rounded-md border border-line p-0.5">
          {DIMS.map(([v, label]) => (
            <button
              key={v}
              onClick={() => setDim(v)}
              aria-pressed={dim === v}
              className={`num rounded px-3 py-1 text-xs uppercase tracking-wider transition-colors ${
                dim === v ? "bg-accent/15 font-semibold text-accent" : "text-muted hover:text-ink"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        <div className="inline-flex gap-0.5 rounded-md border border-line p-0.5">
          {(
            [
              ["exportacao", "o Brasil vende"],
              ["importacao", "o Brasil compra"],
            ] as [Fluxo, string][]
          ).map(([v, label]) => (
            <button
              key={v}
              onClick={() => setFluxo(v)}
              aria-pressed={fluxo === v}
              className={`num rounded px-3 py-1 text-xs uppercase tracking-wider transition-colors ${
                fluxo === v ? "bg-accent/15 font-semibold text-accent" : "text-muted hover:text-ink"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {r.erro ? (
        <ErroBox erro={r.erro} aoTentar={r.recarregar} />
      ) : r.carregando && !r.dados ? (
        <Esqueleto linhas={8} />
      ) : linhas.length ? (
        <EmTransicao ativo={r.carregando}>
          <Card className="p-5 sm:p-6">
            <ol className="flex flex-col gap-3">
              {linhas.map((l, i) => (
                <li key={`${l.nome}-${i}`} className="flex items-center gap-3">
                  <span className="num w-6 shrink-0 text-right text-sm text-muted">{i + 1}</span>
                  <div className="min-w-0 flex-1">
                    <div className="mb-1 flex items-baseline justify-between gap-3">
                      <span className="truncate text-sm text-ink/90" title={l.nome}>
                        {l.nome}
                      </span>
                      <span className={`num shrink-0 text-sm ${i === 0 ? "text-accent" : "text-ink"}`}>
                        {usd(l.valor_fob)}
                      </span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-sm bg-surface-2">
                      <div
                        className={`h-full rounded-sm ${fluxo === "exportacao" ? "bg-emerald-500" : "bg-rose-400"}`}
                        style={{ width: `${Math.max((100 * Number(l.valor_fob)) / max, 1.5)}%` }}
                      />
                    </div>
                  </div>
                </li>
              ))}
            </ol>
          </Card>
        </EmTransicao>
      ) : (
        <Vazio>sem dados pra esse recorte.</Vazio>
      )}

      <SeloFonte fonte={fonte} />
    </section>
  );
}

export default function CadernoComercio() {
  return (
    <div>
      <CadernoHeader
        numero="XX"
        kicker="ComexStat · MDIC"
        titulo="Comércio exterior"
        resumo="O que o Brasil vende e compra do mundo: a balança comercial mês a mês e os rankings de parceiros, estados exportadores e produtos — dos dados oficiais da Secretaria de Comércio Exterior."
      />
      <div className="mb-5">
        <BadgeFrescor rotulo="dados mensais" detalhe="o MDIC fecha o mês anterior no início do seguinte" />
      </div>
      <Balanca />
      <Destaques />
      <Rankings />
    </div>
  );
}
