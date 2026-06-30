"use client";

import { useState } from "react";
import { CadernoHeader } from "@/components/Caderno";
import { Card } from "@/components/Card";
import { Carimbo } from "@/components/Carimbo";
import { Kpi } from "@/components/Kpi";
import { BarrasGasto } from "@/components/BarrasGasto";
import { BarrasImposto } from "@/components/BarrasImposto";
import { RankingArrecadacao } from "@/components/RankingArrecadacao";
import { Esqueleto, ErroBox, Vazio, EmTransicao } from "@/components/Estados";
import { useBalcao } from "@/hooks/useBalcao";
import { caminho, formataBRL } from "@/lib/api";
import { UFS, CAPITAIS } from "@/lib/ufs";
import type { Arrecadacao, Municipio, NormalizedResponse } from "@/lib/types";

const ANOS = [2023, 2022, 2021, 2020];
type Nivel = "uniao" | "estado" | "municipio";
const NIVEIS: [Nivel, string][] = [
  ["uniao", "País"],
  ["estado", "Estado"],
  ["municipio", "Cidade"],
];

export default function CadernoTesouro() {
  const [modo, setModo] = useState<"consulta" | "ranking">("consulta");
  const [nivel, setNivel] = useState<Nivel>("estado");
  const [uf, setUf] = useState("GO");
  const [ibge, setIbge] = useState(CAPITAIS["GO"]);
  const [ano, setAno] = useState(2023);

  // ao trocar de nível/UF no modo cidade, já aponta pra capital da UF
  function escolheNivel(n: Nivel) {
    setNivel(n);
    if (n === "municipio") setIbge(CAPITAIS[uf] ?? "");
  }
  function escolheUf(u: string) {
    setUf(u);
    if (nivel === "municipio") setIbge(CAPITAIS[u] ?? "");
  }

  // lista de municípios da UF só quando o nível é cidade
  const munis = useBalcao<NormalizedResponse<Municipio>>(
    nivel === "municipio" ? caminho("ibge/municipios", { uf }) : null,
  );
  const municipios = munis.dados?.dados ?? [];

  const ente = nivel === "uniao" ? "brasil" : nivel === "estado" ? uf : ibge;
  const arr = useBalcao<Arrecadacao>(ente ? caminho("arrecadacao", { ente, ano }) : null);

  const dados = arr.dados;
  const fin = dados?.ente ?? null;
  const impostos = dados?.impostos ?? [];
  const despesas = dados?.despesas ?? [];
  const porFuncao = Object.fromEntries(despesas.map((d) => [d.funcao, d.valor]));
  const aviso = dados?.meta?.aviso as string | undefined;

  const impostoPorHab =
    fin?.receita_impostos && fin.populacao
      ? Number(fin.receita_impostos) / fin.populacao
      : null;

  const titulo = fin?.ente ?? (nivel === "uniao" ? "Brasil" : nivel === "estado" ? uf : "—");
  const carregandoVazio = arr.carregando && !arr.dados;

  return (
    <div>
      <CadernoHeader
        numero="VI"
        kicker="Tesouro Nacional · SICONFI"
        titulo="A arrecadação do Brasil"
        resumo="Quanto a União, cada estado e cada cidade arrecadam em impostos — e pra onde esse dinheiro vai. Direto da Declaração de Contas Anuais. Valores realizados do balanço; 2023 é o ano mais completo. O SICONFI é lento: a primeira consulta de cada ente pode demorar."
      />

      <div className="mb-6 flex flex-wrap items-center gap-x-5 gap-y-3">
        <div className="inline-flex gap-0.5 rounded-md border border-line p-0.5">
          {(
            [
              ["consulta", "Consulta"],
              ["ranking", "Ranking"],
            ] as ["consulta" | "ranking", string][]
          ).map(([v, label]) => (
            <button
              key={v}
              onClick={() => setModo(v)}
              aria-pressed={modo === v}
              className={`num rounded px-3 py-1 text-xs uppercase tracking-wider transition-colors ${
                modo === v ? "bg-accent/15 font-semibold text-accent" : "text-muted hover:text-ink"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        <div className="flex gap-1">
          {ANOS.map((a) => (
            <button
              key={a}
              onClick={() => setAno(a)}
              aria-pressed={a === ano}
              className={`num rounded px-1.5 py-0.5 text-xs transition-colors ${
                a === ano
                  ? "text-ink underline decoration-accent decoration-2 underline-offset-4"
                  : "text-muted"
              }`}
            >
              {a}
            </button>
          ))}
        </div>
      </div>

      {modo === "ranking" ? (
        <RankingArrecadacao ano={ano} />
      ) : (
        <>
      <div className="mb-6 flex flex-wrap items-center gap-x-5 gap-y-3">
        <div className="inline-flex gap-0.5 rounded-md border border-line p-0.5">
          {NIVEIS.map(([v, label]) => (
            <button
              key={v}
              onClick={() => escolheNivel(v)}
              aria-pressed={nivel === v}
              className={`num rounded px-3 py-1 text-xs uppercase tracking-wider transition-colors ${
                nivel === v ? "bg-accent/15 font-semibold text-accent" : "text-muted hover:text-ink"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {nivel !== "uniao" && (
          <label className="num flex items-center gap-2 text-xs uppercase tracking-wider text-muted">
            UF
            <select
              value={uf}
              onChange={(e) => escolheUf(e.target.value)}
              className="rounded-md border border-line bg-surface px-2 py-1 text-ink"
            >
              {UFS.map((u) => (
                <option key={u} value={u}>
                  {u}
                </option>
              ))}
            </select>
          </label>
        )}

        {nivel === "municipio" && (
          <label className="num flex items-center gap-2 text-xs uppercase tracking-wider text-muted">
            Cidade
            <select
              value={ibge}
              onChange={(e) => setIbge(e.target.value)}
              disabled={!municipios.length}
              className="max-w-56 rounded-md border border-line bg-surface px-2 py-1 text-ink disabled:opacity-50"
            >
              {municipios.length ? (
                municipios.map((m) => (
                  <option key={m.id} value={String(m.id)}>
                    {m.nome}
                  </option>
                ))
              ) : (
                <option value={ibge}>carregando…</option>
              )}
            </select>
          </label>
        )}

      </div>

      <Card className="p-5 pt-6">
        <div className="flex items-start justify-between gap-3 pl-5">
          <div>
            <h2 className="font-display text-2xl leading-tight text-ink">
              {titulo} · {ano}
            </h2>
            <p className="num text-xs text-muted">
              {fin?.populacao
                ? `${fin.populacao.toLocaleString("pt-BR")} habitantes`
                : "Tesouro Nacional · SICONFI"}
            </p>
          </div>
          <Carimbo
            fonte="TESOURO"
            cache={arr.dados?.meta?.cache as string | undefined}
            ms={arr.ms}
            erro={!!arr.erro}
          />
        </div>

        <div className="my-5 pl-5">
          {arr.erro ? (
            <ErroBox erro={arr.erro} aoTentar={arr.recarregar} />
          ) : carregandoVazio ? (
            <Esqueleto linhas={3} />
          ) : fin ? (
            <EmTransicao ativo={arr.carregando}>
              <div className="flex flex-wrap gap-8">
                <Kpi rotulo="Receita · R$ bi" valor={Number(fin.receita_total) / 1e9} formato="decimal" tom="accent-2" />
                {fin.receita_impostos != null && (
                  <Kpi rotulo="Impostos · R$ bi" valor={Number(fin.receita_impostos) / 1e9} formato="decimal" tom="accent" />
                )}
                <Kpi rotulo="Despesa · R$ bi" valor={Number(fin.despesa_total) / 1e9} formato="decimal" tom="ink" />
              </div>
              {impostoPorHab != null && (
                <p className="mt-5 font-editorial text-[1.02rem] italic text-ink/70">
                  ≈ {formataBRL(impostoPorHab)} arrecadados em impostos por habitante.
                </p>
              )}
            </EmTransicao>
          ) : (
            <Vazio>{aviso ?? "o Tesouro não tem contas desse ente nesse ano."}</Vazio>
          )}
        </div>
      </Card>

      <div className="mt-7 grid gap-7 md:grid-cols-2">
        <section>
          <p className="kicker mb-3">De onde vem · por imposto</p>
          {arr.erro ? null : carregandoVazio ? (
            <Esqueleto linhas={5} />
          ) : impostos.length ? (
            <EmTransicao ativo={arr.carregando}>
              <Card className="p-5 pl-7">
                <BarrasImposto impostos={impostos} />
              </Card>
            </EmTransicao>
          ) : (
            <Vazio>sem impostos registrados em {ano}.</Vazio>
          )}
        </section>

        <section>
          <p className="kicker mb-3">Pra onde vai · por função</p>
          {arr.erro ? null : carregandoVazio ? (
            <Esqueleto linhas={5} />
          ) : despesas.length ? (
            <EmTransicao ativo={arr.carregando}>
              <Card className="p-5 pl-7">
                <BarrasGasto porTipo={porFuncao} />
              </Card>
            </EmTransicao>
          ) : (
            <Vazio>sem despesa por função em {ano}.</Vazio>
          )}
        </section>
      </div>
        </>
      )}
    </div>
  );
}
