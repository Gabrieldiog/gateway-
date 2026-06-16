"use client";

import { useState } from "react";
import { CadernoHeader } from "@/components/Caderno";
import { Card } from "@/components/Card";
import { Carimbo } from "@/components/Carimbo";
import { Kpi } from "@/components/Kpi";
import { BarrasGasto } from "@/components/BarrasGasto";
import { Esqueleto, ErroBox, Vazio } from "@/components/Estados";
import { useBalcao } from "@/hooks/useBalcao";
import { caminho, formataBRL } from "@/lib/api";
import { UFS } from "@/lib/ufs";
import type { DespesaFuncao, FinancaEstado, NormalizedResponse } from "@/lib/types";

const ANOS = [2023, 2022, 2021, 2020];

export default function CadernoTesouro() {
  const [uf, setUf] = useState("SP");
  const [ano, setAno] = useState(2023);

  const panorama = useBalcao<NormalizedResponse<FinancaEstado>>(
    caminho(`tesouro/estados/${uf}`, { ano }),
  );
  const despesas = useBalcao<NormalizedResponse<DespesaFuncao>>(
    caminho(`tesouro/estados/${uf}/despesas`, { ano }),
  );

  const fin = panorama.dados?.dados?.[0] ?? null;
  const aviso = panorama.dados?.meta?.aviso as string | undefined;
  const funcoes = despesas.dados?.dados ?? [];
  const porFuncao = Object.fromEntries(funcoes.map((f) => [f.funcao, f.valor]));

  const impostoPorHab =
    fin?.receita_impostos && fin.populacao
      ? Number(fin.receita_impostos) / fin.populacao
      : null;

  return (
    <div>
      <CadernoHeader
        numero="VI"
        kicker="Tesouro Nacional · SICONFI"
        titulo="As contas dos estados"
        resumo="Quanto cada estado arrecada, quanto disso vem de impostos e onde gasta — direto da Declaração de Contas Anuais. Os valores estão em bilhões de reais. O SICONFI é lento: a primeira consulta de cada estado pode demorar."
      />

      <div className="mb-6 flex flex-wrap items-center gap-4">
        <label className="num flex items-center gap-2 text-xs uppercase tracking-wider text-muted">
          UF
          <select
            value={uf}
            onChange={(e) => setUf(e.target.value)}
            className="rounded-md border border-line bg-surface px-2 py-1 text-ink"
          >
            {UFS.map((u) => (
              <option key={u} value={u}>
                {u}
              </option>
            ))}
          </select>
        </label>
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

      <Card className="p-5 pt-6">
        <div className="flex items-start justify-between gap-3 pl-5">
          <div>
            <h2 className="font-display text-2xl leading-tight text-ink">
              {uf} · {ano}
            </h2>
            <p className="num text-xs text-muted">
              {fin?.populacao
                ? `${fin.populacao.toLocaleString("pt-BR")} habitantes`
                : "Tesouro Nacional"}
            </p>
          </div>
          <Carimbo
            fonte="TESOURO"
            cache={panorama.dados?.meta?.cache as string | undefined}
            ms={panorama.ms}
            erro={!!panorama.erro}
          />
        </div>

        <div className="my-5 pl-5">
          {panorama.erro ? (
            <ErroBox erro={panorama.erro} aoTentar={panorama.recarregar} />
          ) : panorama.carregando && !panorama.dados ? (
            <Esqueleto linhas={3} />
          ) : fin ? (
            <>
              <div className="flex flex-wrap gap-8">
                <Kpi rotulo="Receita · R$ bi" valor={Number(fin.receita_total) / 1e9} formato="decimal" tom="accent-2" />
                {fin.receita_impostos != null && (
                  <Kpi rotulo="Impostos · R$ bi" valor={Number(fin.receita_impostos) / 1e9} formato="decimal" tom="accent" />
                )}
                <Kpi rotulo="Despesa · R$ bi" valor={Number(fin.despesa_total) / 1e9} formato="decimal" tom="ink" />
              </div>
              {impostoPorHab != null && (
                <p className="mt-5 font-editorial text-[1.02rem] italic text-ink/70">
                  ≈ {formataBRL(impostoPorHab)} arrecadados em impostos por
                  habitante.
                </p>
              )}
            </>
          ) : (
            <Vazio>{aviso ?? "o Tesouro não tem contas desse estado nesse ano."}</Vazio>
          )}
        </div>
      </Card>

      <div className="mt-7">
        <p className="kicker mb-3">Onde {uf} gasta · despesa por função</p>
        {despesas.erro ? (
          <ErroBox erro={despesas.erro} aoTentar={despesas.recarregar} />
        ) : despesas.carregando && !despesas.dados ? (
          <Esqueleto linhas={6} />
        ) : funcoes.length ? (
          <Card className="p-5 pl-7">
            <BarrasGasto porTipo={porFuncao} />
          </Card>
        ) : (
          <Vazio>sem despesa por função registrada em {ano}.</Vazio>
        )}
      </div>
    </div>
  );
}
