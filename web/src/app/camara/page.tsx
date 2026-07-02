"use client";

/* eslint-disable @next/next/no-img-element */
import { useEffect, useState } from "react";
import { CadernoHeader } from "@/components/Caderno";
import { Card } from "@/components/Card";
import { Carimbo } from "@/components/Carimbo";
import { Kpi } from "@/components/Kpi";
import { BarrasGasto } from "@/components/BarrasGasto";
import { Seletor } from "@/components/Seletor";
import { Esqueleto, ErroBox, Vazio, EmTransicao } from "@/components/Estados";
import { useBalcao } from "@/hooks/useBalcao";
import { apiGet, caminho, formataBRL } from "@/lib/api";
import { UFS } from "@/lib/ufs";
import { PARTIDOS } from "@/lib/partidos";
import type { Deputado, GastosOut, NormalizedResponse } from "@/lib/types";

// "todos" agrega o mandato inteiro (legislatura 57)
type AnoSel = number | "todos";
const OPCOES_ANO: AnoSel[] = ["todos", 2026, 2025, 2024, 2023];
const ANOS_MANDATO = [2023, 2024, 2025, 2026];

export default function CadernoCamara() {
  const [uf, setUf] = useState("SP");
  const [partido, setPartido] = useState("");
  const [sel, setSel] = useState<Deputado | null>(null);
  const [ano, setAno] = useState<AnoSel>(2024);

  const lista = useBalcao<NormalizedResponse<Deputado>>(
    caminho("camara/deputados", { uf, partido: partido || undefined, itens: 30 }),
  );
  const deputados = lista.dados?.dados ?? [];

  // mantém uma seleção válida conforme a lista muda
  useEffect(() => {
    if (!deputados.length) {
      setSel(null);
      return;
    }
    setSel((atual) => {
      if (atual && deputados.some((d) => d.id === atual.id)) return atual;
      return deputados[0];
    });
  }, [deputados]);

  return (
    <div>
      <CadernoHeader
        numero="II"
        kicker="Câmara dos Deputados"
        titulo="Quem são e quanto gastam"
        resumo="A lista de deputados em exercício e, para cada um, a cota parlamentar (CEAP) agregada por tipo de despesa. Filtre por estado ou partido e escolha um nome."
      />

      <div className="mb-6 flex flex-wrap items-center gap-3">
        <label className="num flex items-center gap-2 text-xs uppercase tracking-wider text-muted">
          UF
          <Seletor value={uf} onChange={(e) => setUf(e.target.value)}>
            {UFS.map((u) => (
              <option key={u} value={u}>
                {u}
              </option>
            ))}
          </Seletor>
        </label>
        <label className="num flex items-center gap-2 text-xs uppercase tracking-wider text-muted">
          Partido
          <Seletor
            value={PARTIDOS.includes(partido) ? partido : ""}
            onChange={(e) => setPartido(e.target.value)}
          >
            <option value="">todos</option>
            {PARTIDOS.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </Seletor>
        </label>
        <input
          value={partido}
          onChange={(e) => setPartido(e.target.value.toUpperCase())}
          placeholder="ou digite"
          className="w-24 rounded-md border border-line bg-surface px-2 py-1 text-sm uppercase text-ink placeholder:normal-case placeholder:text-muted"
        />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_1.1fr]">
        {/* lista de deputados */}
        <div>
          <p className="kicker mb-3">
            {lista.carregando && !lista.dados
              ? "consultando…"
              : `${deputados.length} deputados · ${uf}`}
          </p>
          {lista.erro ? (
            <ErroBox erro={lista.erro} aoTentar={lista.recarregar} />
          ) : lista.carregando && !lista.dados ? (
            <Esqueleto linhas={8} />
          ) : deputados.length === 0 ? (
            <Vazio>nenhum deputado para esse filtro.</Vazio>
          ) : (
            <EmTransicao ativo={lista.carregando}>
              <ul className="flex max-h-160 flex-col gap-1 overflow-y-auto pr-1">
                {deputados.map((d) => {
                  const ativo = sel?.id === d.id;
                  return (
                    <li key={d.id}>
                      <button
                        onClick={() => setSel(d)}
                        className={`flex w-full items-center gap-3 rounded-md border px-3 py-2 text-left transition-colors ${
                          ativo ? "border-accent/40 bg-surface" : "border-transparent hover:bg-surface/70"
                        }`}
                      >
                        <span className="h-10 w-8 shrink-0 overflow-hidden rounded-sm border border-line bg-surface-2">
                          {d.foto && (
                            <img src={d.foto} alt="" loading="lazy" className="h-full w-full object-cover" />
                          )}
                        </span>
                        <span className="min-w-0">
                          <span className="block truncate text-ink">{d.nome}</span>
                          <span className="num text-xs text-muted">
                            {[d.partido, d.uf].filter(Boolean).join(" · ")}
                          </span>
                        </span>
                        {ativo && <span className="ml-auto h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />}
                      </button>
                    </li>
                  );
                })}
              </ul>
            </EmTransicao>
          )}
        </div>

        {/* painel de gastos do selecionado */}
        <div>
          <div className="mb-3 flex items-center justify-between">
            <p className="kicker">Cota parlamentar</p>
            <div className="flex gap-1">
              {OPCOES_ANO.map((a) => (
                <button
                  key={a}
                  onClick={() => setAno(a)}
                  aria-pressed={a === ano}
                  className={`num rounded px-1.5 py-0.5 text-xs transition-colors ${
                    a === ano ? "text-ink underline decoration-accent decoration-2 underline-offset-4" : "text-muted"
                  }`}
                >
                  {a === "todos" ? "Todos" : a}
                </button>
              ))}
            </div>
          </div>
          {!sel ? (
            <Vazio>escolha um deputado.</Vazio>
          ) : ano === "todos" ? (
            <PainelTodosAnos deputado={sel} />
          ) : (
            <PainelGastos deputado={sel} ano={ano} />
          )}
        </div>
      </div>
    </div>
  );
}

function PainelGastos({ deputado, ano }: { deputado: Deputado; ano: number }) {
  const { dados, carregando, erro, ms, recarregar } = useBalcao<GastosOut>(
    caminho("gastos", { deputado: deputado.id, ano }),
  );

  return (
    <Card className="p-5 pt-6">
      <div className="flex items-start justify-between gap-3 pl-5">
        <div>
          <h2 className="font-display text-2xl leading-tight text-ink">{deputado.nome}</h2>
          <p className="num text-xs text-muted">
            {[deputado.partido, deputado.uf].filter(Boolean).join(" · ")} · {ano}
          </p>
        </div>
        <Carimbo fonte="CÂMARA" ms={ms} erro={!!erro} />
      </div>

      <div className="my-5 pl-5">
        {erro ? (
          <ErroBox erro={erro} aoTentar={recarregar} />
        ) : carregando && !dados ? (
          <Esqueleto linhas={5} />
        ) : dados ? (
          <EmTransicao ativo={carregando}>
            <div className="mb-5 flex flex-wrap gap-8">
              <Kpi rotulo="Total no ano" valor={Number(dados.valor_total)} formato="brl" tom="accent" />
              <Kpi rotulo="Documentos" valor={dados.total_documentos} />
            </div>
            {dados.total_documentos > 0 ? (
              <BarrasGasto porTipo={dados.por_tipo} />
            ) : (
              <Vazio>nenhuma despesa registrada em {ano}.</Vazio>
            )}
          </EmTransicao>
        ) : null}
      </div>
    </Card>
  );
}

// "todos os anos": busca cada ano do mandato em paralelo e mostra a barra por ano
function PainelTodosAnos({ deputado }: { deputado: Deputado }) {
  const [estado, setEstado] = useState<{
    carregando: boolean;
    anos: { ano: number; total: number; docs: number }[];
  }>({ carregando: true, anos: [] });

  useEffect(() => {
    let vivo = true;
    setEstado({ carregando: true, anos: [] });
    Promise.all(
      ANOS_MANDATO.map((a) =>
        apiGet<GastosOut>(caminho("gastos", { deputado: deputado.id, ano: a }))
          .then((r) => ({ ano: a, total: Number(r.valor_total), docs: r.total_documentos }))
          .catch(() => ({ ano: a, total: 0, docs: 0 })),
      ),
    ).then((res) => {
      if (vivo) setEstado({ carregando: false, anos: res });
    });
    return () => {
      vivo = false;
    };
  }, [deputado.id]);

  const max = Math.max(...estado.anos.map((a) => a.total), 1);
  const totalGeral = estado.anos.reduce((s, a) => s + a.total, 0);
  const docsGeral = estado.anos.reduce((s, a) => s + a.docs, 0);

  return (
    <Card className="p-5 pt-6">
      <div className="flex items-start justify-between gap-3 pl-5">
        <div>
          <h2 className="font-display text-2xl leading-tight text-ink">{deputado.nome}</h2>
          <p className="num text-xs text-muted">
            {[deputado.partido, deputado.uf].filter(Boolean).join(" · ")} · mandato 2023–2026
          </p>
        </div>
        <Carimbo fonte="CÂMARA" ms={null} />
      </div>

      <div className="my-5 pl-5">
        {estado.carregando ? (
          <Esqueleto linhas={4} />
        ) : (
          <>
            <div className="mb-5 flex flex-wrap gap-8">
              <Kpi rotulo="Total no mandato" valor={totalGeral} formato="brl" tom="accent" />
              <Kpi rotulo="Documentos" valor={docsGeral} />
            </div>
            <ul className="flex flex-col gap-2.5">
              {estado.anos.map((a) => (
                <li key={a.ano}>
                  <div className="mb-1 flex items-baseline justify-between">
                    <span className="num text-sm text-ink/85">{a.ano}</span>
                    <span className="num text-sm text-muted">{formataBRL(a.total)}</span>
                  </div>
                  <div className="h-2.5 overflow-hidden rounded-sm bg-surface-2">
                    <div
                      className="h-full rounded-sm bg-accent-2"
                      style={{ width: `${Math.max((a.total / max) * 100, 1.5)}%` }}
                    />
                  </div>
                </li>
              ))}
            </ul>
          </>
        )}
      </div>
    </Card>
  );
}
