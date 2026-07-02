"use client";

import { useState } from "react";
import { CadernoHeader } from "@/components/Caderno";
import { Card } from "@/components/Card";
import { Carimbo } from "@/components/Carimbo";
import { BadgeFrescor } from "@/components/Frescor";
import { Kpi } from "@/components/Kpi";
import { SeloFonte } from "@/components/SeloFonte";
import { Esqueleto, ErroBox, Vazio, EmTransicao } from "@/components/Estados";
import { useBalcao } from "@/hooks/useBalcao";
import { caminho } from "@/lib/api";
import type { FonteDado, NormalizedResponse, Queimada } from "@/lib/types";

type Por = "estado" | "bioma" | "municipio";

const POR: [Por, string][] = [
  ["estado", "Estado"],
  ["bioma", "Bioma"],
  ["municipio", "Município"],
];

const DATAS = [
  { label: "Ontem", offset: 1 },
  { label: "Hoje", offset: 0 },
  { label: "-2 dias", offset: 2 },
  { label: "-3 dias", offset: 3 },
];

// cor de cada bioma; estado/município usam tons de fogo
const BIOMA_COR: Record<string, string> = {
  Cerrado: "#d97706",
  Amazônia: "#059669",
  "Mata Atlântica": "#0d9488",
  Caatinga: "#ca8a04",
  Pantanal: "#7c3aed",
  Pampa: "#65a30d",
};
const FOGO = "#ea580c";
const FOGO_TOPO = "#dc2626";

// data local em YYYY-MM-DD, N dias atrás (o arquivo do INPE é por dia)
function dataISO(offset: number): string {
  const d = new Date();
  d.setDate(d.getDate() - offset);
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const dia = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${m}-${dia}`;
}

function corDe(por: Por, nome: string, topo: boolean): string {
  if (por === "bioma") return BIOMA_COR[nome] ?? FOGO;
  return topo ? FOGO_TOPO : FOGO;
}

export default function CadernoQueimadas() {
  const [por, setPor] = useState<Por>("estado");
  const [offset, setOffset] = useState(1); // ontem: dia completo

  const data = dataISO(offset);
  const q = useBalcao<NormalizedResponse<Queimada>>(
    caminho("inpe/queimadas", { por, data, limit: por === "municipio" ? 30 : 27 }),
  );

  const linhas = q.dados?.dados ?? [];
  const max = linhas.length ? linhas[0].focos : 1;
  const total = (q.dados?.meta?.total_focos as number | undefined) ?? 0;
  const fonte = q.dados?.meta?.fonte as FonteDado | undefined;
  const rotuloData = DATAS.find((d) => d.offset === offset)?.label ?? data;

  return (
    <div>
      <CadernoHeader
        numero="XVI"
        kicker="INPE · Programa Queimadas"
        titulo="Queimadas"
        resumo="Focos de incêndio detectados por satélite no Brasil, agregados por estado e bioma. O INPE atualiza o arquivo do dia ao longo das horas — o Balcão transforma milhares de pontos crus num ranking pronto."
      />

      <div className="mb-5 flex flex-wrap items-center gap-x-5 gap-y-3">
        <div className="inline-flex gap-0.5 rounded-md border border-line p-0.5">
          {POR.map(([v, label]) => (
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
        <div className="flex flex-wrap items-center gap-2">
          {DATAS.map((d) => (
            <button
              key={d.offset}
              onClick={() => setOffset(d.offset)}
              aria-pressed={offset === d.offset}
              className={`num rounded-full border px-3 py-1 text-xs uppercase tracking-wider transition-colors ${
                offset === d.offset
                  ? "border-accent bg-accent text-surface"
                  : "border-line text-muted hover:border-accent hover:text-accent"
              }`}
            >
              {d.label}
            </button>
          ))}
        </div>
      </div>

      <div className="mb-3">
        <BadgeFrescor
          rotulo="satélite · atualiza ao longo do dia"
          detalhe={offset === 0 ? "o dia de hoje ainda está enchendo" : undefined}
        />
      </div>

      <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
        <Kpi rotulo={`focos no Brasil · ${rotuloData}`} valor={total} sufixo="focos" tom="accent" />
        <Carimbo fonte="INPE" ms={q.ms} erro={!!q.erro} />
      </div>

      {q.erro ? (
        // 404 aqui não é defeito: o arquivo daquele dia ainda não existe no
        // servidor do INPE (o de hoje só aparece ao longo da manhã)
        q.erro.status === 404 ? (
          <Vazio>
            o INPE ainda não publicou o arquivo de {rotuloData.toLowerCase()} — o dia costuma
            aparecer ao longo da manhã e ir crescendo até a noite. Enquanto isso, veja
            &ldquo;Ontem&rdquo;, que já está completo.
          </Vazio>
        ) : (
          <ErroBox erro={q.erro} aoTentar={q.recarregar} />
        )
      ) : q.carregando && !q.dados ? (
        <Esqueleto linhas={10} />
      ) : linhas.length ? (
        <EmTransicao ativo={q.carregando}>
          <Card className="p-5 sm:p-6">
            <ol className="flex flex-col gap-3">
              {linhas.map((l, i) => {
                const cor = corDe(por, l.nome, i === 0);
                return (
                  <li key={l.nome} className="flex items-center gap-3">
                    <span className="num w-6 shrink-0 text-right text-sm text-muted">{i + 1}</span>
                    <div className="min-w-0 flex-1">
                      <div className="mb-1 flex items-baseline justify-between gap-3">
                        <span className="truncate text-sm text-ink/90" title={l.nome}>
                          {l.nome}
                        </span>
                        <span className="num shrink-0 text-sm text-ink">
                          {l.focos.toLocaleString("pt-BR")}
                          <span className="ml-1 text-xs text-muted">focos</span>
                        </span>
                      </div>
                      <div className="h-2 overflow-hidden rounded-sm bg-surface-2">
                        <div
                          className="h-full rounded-sm transition-all duration-500"
                          style={{ width: `${Math.max((l.focos / max) * 100, 1.5)}%`, background: cor }}
                        />
                      </div>
                    </div>
                  </li>
                );
              })}
            </ol>
            <p className="mt-5 border-t border-line pt-3 font-editorial text-sm italic text-muted">
              {total.toLocaleString("pt-BR")} focos detectados no Brasil em {rotuloData}
              {offset === 0 && " (o dia ainda está sendo consolidado)"}. Um foco é um pixel quente
              visto por satélite, não necessariamente um incêndio distinto.
            </p>
          </Card>
        </EmTransicao>
      ) : (
        <Vazio>nenhum foco detectado em {rotuloData}.</Vazio>
      )}

      <SeloFonte fonte={fonte} />
    </div>
  );
}
