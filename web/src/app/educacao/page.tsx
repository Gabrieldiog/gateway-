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
import { caminho } from "@/lib/api";
import { CAPITAIS, UFS } from "@/lib/ufs";
import type { FonteDado, IndicadorEducacao, Municipio, NormalizedResponse } from "@/lib/types";

const REDES: [string, string][] = [
  ["publica", "Pública"],
  ["municipal", "Municipal"],
  ["estadual", "Estadual"],
  ["privada", "Privada"],
];

const TEMAS: [string, string][] = [
  ["matriculas", "Matrículas"],
  ["docentes", "Docentes"],
  ["escolas", "Escolas"],
];

// o IDEB vai de 0 a 10; a leitura editorial da cor: verde bom, ocre atenção, vermelho ruim
function corIdeb(nota: number | null): string {
  if (nota == null) return "text-muted";
  if (nota >= 6) return "text-ok";
  if (nota >= 4) return "text-ocre";
  return "text-erro";
}

// mini gráfico de barras da evolução; no IDEB a escala é fixa 0–10, no Censo é relativa
function Evolucao({
  serie,
  escalaFixa,
}: {
  serie: { ano: number; valor: number }[];
  escalaFixa?: number;
}) {
  if (serie.length < 2) return null;
  const max = escalaFixa ?? Math.max(...serie.map((p) => p.valor));
  const min = escalaFixa ? 0 : Math.min(...serie.map((p) => p.valor));
  const altura = (v: number) =>
    escalaFixa ? (v / escalaFixa) * 100 : max === min ? 60 : 18 + ((v - min) / (max - min)) * 82;
  return (
    <div className="mt-3 flex h-12 items-end gap-[3px]">
      {serie.map((p) => (
        <div
          key={p.ano}
          title={`${p.ano}: ${p.valor.toLocaleString("pt-BR")}`}
          className="min-w-0 flex-1 rounded-t-sm bg-accent-2/45 transition-colors hover:bg-accent-2"
          style={{ height: `${Math.max(4, altura(p.valor))}%` }}
        />
      ))}
    </div>
  );
}

function Ideb({ ibge }: { ibge: string }) {
  const [rede, setRede] = useState("publica");
  const r = useBalcao<NormalizedResponse<IndicadorEducacao>>(
    caminho("educacao/ideb", { municipio: ibge, rede }),
  );
  const etapas = r.dados?.dados ?? [];

  return (
    <section className="mb-10">
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <h2 className="font-display text-lg font-semibold text-ink">
          <Termo t="ideb">IDEB</Termo> — a nota da escola
        </h2>
        <div className="inline-flex flex-wrap gap-0.5 rounded-md border border-line p-0.5">
          {REDES.map(([v, label]) => (
            <button
              key={v}
              onClick={() => setRede(v)}
              aria-pressed={rede === v}
              className={`num rounded px-3 py-1 text-xs uppercase tracking-wider transition-colors ${
                rede === v ? "bg-accent/15 font-semibold text-accent" : "text-muted hover:text-ink"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        <Carimbo fonte="INEP" cache={r.dados?.meta?.cache as string | undefined} ms={r.ms} erro={!!r.erro} />
      </div>
      {r.erro ? (
        <ErroBox erro={r.erro} aoTentar={r.recarregar} />
      ) : r.carregando && !r.dados ? (
        <Esqueleto linhas={5} />
      ) : (
        <EmTransicao ativo={r.carregando}>
          <div className="grid gap-3 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
            {etapas.map((e) => (
              <Card key={e.etapa} className="p-5">
                <p className="kicker">{e.etapa}</p>
                {e.ultimo_valor != null ? (
                  <>
                    <p className={`num mt-1 font-display text-4xl font-semibold ${corIdeb(e.ultimo_valor)}`}>
                      {e.ultimo_valor.toLocaleString("pt-BR")}
                    </p>
                    <p className="num mt-0.5 text-xs text-muted">
                      de 0 a 10 · {e.ultimo_ano}
                      {e.serie.length > 1 && ` · desde ${e.serie[0].ano}`}
                    </p>
                    <Evolucao serie={e.serie} escalaFixa={10} />
                  </>
                ) : (
                  <p className="mt-2 font-editorial text-sm italic text-muted">
                    a rede {rede} não oferece esta etapa aqui.
                  </p>
                )}
              </Card>
            ))}
          </div>
        </EmTransicao>
      )}
    </section>
  );
}

function Censo({ ibge }: { ibge: string }) {
  const [tema, setTema] = useState("matriculas");
  const r = useBalcao<NormalizedResponse<IndicadorEducacao>>(
    caminho("educacao/censo", { municipio: ibge, tema }),
  );
  const etapas = r.dados?.dados ?? [];
  const rotulo = TEMAS.find(([v]) => v === tema)?.[1] ?? "";

  return (
    <section>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <h2 className="font-display text-lg font-semibold text-ink">O tamanho da rede</h2>
        <div className="inline-flex gap-0.5 rounded-md border border-line p-0.5">
          {TEMAS.map(([v, label]) => (
            <button
              key={v}
              onClick={() => setTema(v)}
              aria-pressed={tema === v}
              className={`num rounded px-3 py-1 text-xs uppercase tracking-wider transition-colors ${
                tema === v ? "bg-accent/15 font-semibold text-accent" : "text-muted hover:text-ink"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
      <p className="mb-4 max-w-2xl font-editorial text-sm leading-relaxed text-ink/75">
        {rotulo} da rede pública e privada juntas, pelo Censo Escolar mais recente — e como o
        número mudou ao longo dos anos.
      </p>
      {r.erro ? (
        <ErroBox erro={r.erro} aoTentar={r.recarregar} />
      ) : r.carregando && !r.dados ? (
        <Esqueleto linhas={4} />
      ) : etapas.length ? (
        <EmTransicao ativo={r.carregando}>
          <div className="grid gap-3 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
            {etapas.map((e) => (
              <Card key={e.etapa} className="p-5">
                <p className="kicker">{e.etapa}</p>
                {e.ultimo_valor != null ? (
                  <>
                    <p className="num mt-1 font-display text-xl sm:text-2xl lg:text-3xl font-semibold text-ink">
                      {Math.round(e.ultimo_valor).toLocaleString("pt-BR")}
                    </p>
                    <p className="num mt-0.5 text-xs text-muted">
                      {rotulo.toLowerCase()} · {e.ultimo_ano}
                    </p>
                    <Evolucao serie={e.serie} />
                  </>
                ) : (
                  <p className="mt-2 font-editorial text-sm italic text-muted">
                    sem registro nesta etapa.
                  </p>
                )}
              </Card>
            ))}
          </div>
        </EmTransicao>
      ) : (
        <Vazio>o Censo não tem dados desta cidade agora.</Vazio>
      )}
      <SeloFonte fonte={r.dados?.meta?.fonte as FonteDado | undefined} />
    </section>
  );
}

export default function CadernoEducacao() {
  const [uf, setUf] = useState("GO");
  const [ibge, setIbge] = useState(CAPITAIS.GO);

  const cidades = useBalcao<NormalizedResponse<Municipio>>(caminho("ibge/municipios", { uf }));
  const municipios = cidades.dados?.dados ?? [];

  // mesma chamada que o filho Censo faz com o tema default: o cache do gateway dedup,
  // e daqui a gente pesca o ano do Censo mais recente pra carimbar no selo de frescor
  const censo = useBalcao<NormalizedResponse<IndicadorEducacao>>(
    caminho("educacao/censo", { municipio: ibge, tema: "matriculas" }),
  );
  const anoCenso = censo.dados?.dados?.find((e) => e.ultimo_ano != null)?.ultimo_ano ?? null;

  return (
    <div>
      <CadernoHeader
        numero="XXXVI"
        kicker="INEP · IDEB e Censo Escolar"
        titulo="Educação"
        resumo="Como vai a escola da sua cidade: a nota do IDEB rede por rede, etapa por etapa, e o tamanho real da rede de ensino — quantas matrículas, quantos professores, quantas escolas. Traço no lugar da nota é ano que o INEP não divulgou."
        referencia={anoCenso ? `Censo ${anoCenso}` : undefined}
      />

      <div className="mb-6 flex flex-wrap items-center gap-3">
        <Seletor
          value={uf}
          onChange={(e) => {
            setUf(e.target.value);
            setIbge(CAPITAIS[e.target.value]);
          }}
          aria-label="estado"
        >
          {UFS.map((u) => (
            <option key={u}>{u}</option>
          ))}
        </Seletor>
        <Seletor value={ibge} onChange={(e) => setIbge(e.target.value)} aria-label="município">
          {cidades.carregando && <option>carregando…</option>}
          {municipios.map((m) => (
            <option key={m.id} value={m.id}>
              {m.nome}
            </option>
          ))}
        </Seletor>
      </div>

      <Ideb ibge={ibge} />
      <Censo ibge={ibge} />
    </div>
  );
}
