"use client";

import { useState } from "react";
import { CadernoHeader } from "@/components/Caderno";
import { Card } from "@/components/Card";
import { Carimbo } from "@/components/Carimbo";
import { Esqueleto, ErroBox, Vazio, EmTransicao } from "@/components/Estados";
import { useBalcao } from "@/hooks/useBalcao";
import { caminho, formataData } from "@/lib/api";
import type { NormalizedResponse, Votacao } from "@/lib/types";

interface Proposicao {
  fonte: string;
  id: number;
  tipo: string;
  numero: number | null;
  ano: number | null;
  ementa: string;
}

type Aba = "votacoes" | "proposicoes";

const ABAS: [Aba, string][] = [
  ["votacoes", "Votações"],
  ["proposicoes", "Proposições"],
];

const PERIODOS = [
  { dias: 7, label: "7 dias" },
  { dias: 15, label: "15 dias" },
  { dias: 30, label: "30 dias" },
];

const TIPOS = ["", "PL", "PEC", "PLP", "MPV"];

function dataISO(diasAtras: number): string {
  const d = new Date();
  d.setDate(d.getDate() - diasAtras);
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const dia = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${m}-${dia}`;
}

function Votacoes({ dias }: { dias: number }) {
  const r = useBalcao<NormalizedResponse<Votacao>>(
    caminho("camara/votacoes", { data_inicio: dataISO(dias), data_fim: dataISO(0), itens: 30 }),
  );
  const votacoes = r.dados?.dados ?? [];

  return (
    <div>
      <p className="kicker mb-3 flex items-center justify-between">
        <span>o plenário decidiu</span>
        <Carimbo fonte="CÂMARA" cache={r.dados?.meta?.cache as string | undefined} ms={r.ms} erro={!!r.erro} />
      </p>
      {r.erro ? (
        <ErroBox erro={r.erro} aoTentar={r.recarregar} />
      ) : r.carregando && !r.dados ? (
        <Esqueleto linhas={8} />
      ) : votacoes.length ? (
        <EmTransicao ativo={r.carregando}>
          <Card className="divide-y divide-line p-0">
            {votacoes.map((v) => (
              <div key={v.id} className="flex items-start gap-3 px-5 py-3">
                <span
                  className={`num mt-0.5 shrink-0 rounded-full px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wider ${
                    v.aprovada === true
                      ? "bg-ok/10 text-ok"
                      : v.aprovada === false
                        ? "bg-erro/10 text-erro"
                        : "bg-surface-2 text-muted"
                  }`}
                >
                  {v.aprovada === true ? "aprovada" : v.aprovada === false ? "rejeitada" : "registro"}
                </span>
                <div className="min-w-0">
                  <p className="font-editorial text-sm leading-snug text-ink/90">{v.descricao}</p>
                  <p className="num mt-1 text-xs text-muted">
                    {formataData(v.data)}
                    {v.orgao && ` · ${v.orgao}`}
                  </p>
                </div>
              </div>
            ))}
          </Card>
        </EmTransicao>
      ) : (
        <Vazio>nenhuma votação no período.</Vazio>
      )}
    </div>
  );
}

function Proposicoes({ dias }: { dias: number }) {
  const [tipo, setTipo] = useState("");
  const [busca, setBusca] = useState("");
  const [buscaAplicada, setBuscaAplicada] = useState("");

  const r = useBalcao<NormalizedResponse<Proposicao>>(
    caminho("camara/proposicoes", {
      data_inicio: dataISO(dias),
      data_fim: dataISO(0),
      tipo: tipo || undefined,
      busca: buscaAplicada || undefined,
      itens: 30,
    }),
  );
  const proposicoes = r.dados?.dados ?? [];

  return (
    <div>
      <form
        className="mb-4 flex flex-wrap items-center gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          setBuscaAplicada(busca.trim());
        }}
      >
        <div className="inline-flex gap-0.5 rounded-md border border-line p-0.5">
          {TIPOS.map((t) => (
            <button
              key={t || "todos"}
              type="button"
              onClick={() => setTipo(t)}
              aria-pressed={tipo === t}
              className={`num rounded px-2.5 py-1 text-xs uppercase tracking-wider transition-colors ${
                tipo === t ? "bg-accent/15 font-semibold text-accent" : "text-muted hover:text-ink"
              }`}
            >
              {t || "todas"}
            </button>
          ))}
        </div>
        <input
          value={busca}
          onChange={(e) => setBusca(e.target.value)}
          placeholder="tema (ex: saúde, imposto)"
          className="rounded-md border border-line bg-surface px-2 py-1.5 text-sm text-ink focus:border-accent focus:outline-none"
        />
        <button
          type="submit"
          className="num rounded-md border border-ink/20 px-3 py-1.5 text-xs uppercase tracking-wider text-ink transition-colors hover:bg-surface-2"
        >
          buscar
        </button>
        <Carimbo fonte="CÂMARA" cache={r.dados?.meta?.cache as string | undefined} ms={r.ms} erro={!!r.erro} />
      </form>

      {r.erro ? (
        <ErroBox erro={r.erro} aoTentar={r.recarregar} />
      ) : r.carregando && !r.dados ? (
        <Esqueleto linhas={8} />
      ) : proposicoes.length ? (
        <EmTransicao ativo={r.carregando}>
          <Card className="divide-y divide-line p-0">
            {proposicoes.map((p) => (
              <div key={p.id} className="px-5 py-3">
                <p className="num text-xs font-semibold uppercase tracking-wider text-accent">
                  {p.tipo} {p.numero}/{p.ano}
                </p>
                <p className="mt-1 font-editorial text-sm leading-snug text-ink/90">{p.ementa}</p>
              </div>
            ))}
          </Card>
        </EmTransicao>
      ) : (
        <Vazio>nada movimentado com esses filtros no período.</Vazio>
      )}
    </div>
  );
}

export default function CadernoPauta() {
  const [aba, setAba] = useState<Aba>("votacoes");
  const [dias, setDias] = useState(7);

  return (
    <div>
      <CadernoHeader
        numero="XVIII"
        kicker="Câmara dos Deputados"
        titulo="Em pauta"
        resumo="O Congresso desta semana: o que o plenário votou e quais projetos andaram. A mesma API oficial da Câmara dos cadernos de gastos e votos, recortada pelo período que interessa — o agora."
      />

      <div className="mb-6 flex flex-wrap items-center gap-4">
        <div className="inline-flex gap-0.5 rounded-md border border-line p-0.5">
          {ABAS.map(([v, label]) => (
            <button
              key={v}
              onClick={() => setAba(v)}
              aria-pressed={aba === v}
              className={`num rounded px-3 py-1 text-xs uppercase tracking-wider transition-colors ${
                aba === v ? "bg-accent/15 font-semibold text-accent" : "text-muted hover:text-ink"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          {PERIODOS.map((p) => (
            <button
              key={p.dias}
              onClick={() => setDias(p.dias)}
              aria-pressed={dias === p.dias}
              className={`num rounded-full border px-3 py-1 text-xs uppercase tracking-wider transition-colors ${
                dias === p.dias
                  ? "border-accent bg-accent text-surface"
                  : "border-line text-muted hover:border-accent hover:text-accent"
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {aba === "votacoes" ? <Votacoes dias={dias} /> : <Proposicoes dias={dias} />}
    </div>
  );
}
