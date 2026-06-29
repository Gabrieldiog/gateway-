"use client";

import { useState } from "react";
import { CadernoHeader } from "@/components/Caderno";
import { Card } from "@/components/Card";
import { Carimbo } from "@/components/Carimbo";
import { Kpi } from "@/components/Kpi";
import { SerieChart } from "@/components/SerieChart";
import { Esqueleto, ErroBox, EmTransicao } from "@/components/Estados";
import { useBalcao } from "@/hooks/useBalcao";
import { caminho, formataData } from "@/lib/api";
import type { NormalizedResponse, PontoSerie } from "@/lib/types";

const SERIES = [
  { id: "selic", nome: "Selic", unidade: "% a.a." },
  { id: "cdi", nome: "CDI", unidade: "% a.a." },
  { id: "ipca", nome: "IPCA", unidade: "% mês" },
  { id: "igpm", nome: "IGP-M", unidade: "% mês" },
  { id: "dolar", nome: "Dólar", unidade: "R$" },
  { id: "euro", nome: "Euro", unidade: "R$" },
];

const JANELAS = [12, 24, 48];

export default function CadernoBacen() {
  const [serie, setSerie] = useState(SERIES[0]);
  const [ultimos, setUltimos] = useState(24);
  const url = caminho(`bacen/${serie.id}`, { ultimos });
  const { dados, carregando, erro, ms, recarregar } = useBalcao<NormalizedResponse<PontoSerie>>(url);

  const pontos = dados?.dados ?? [];
  const ultimo = pontos.at(-1);
  const primeiro = pontos[0];
  const variacao =
    ultimo && primeiro ? Number(ultimo.valor) - Number(primeiro.valor) : null;

  return (
    <div>
      <CadernoHeader
        numero="IV"
        kicker="Banco Central · SGS"
        titulo="Séries econômicas"
        resumo="Selic, CDI, inflação e câmbio direto do Sistema Gerenciador de Séries do Banco Central. O Balcão fala ISO 8601 e traduz para o dd/mm/aaaa que a fonte exige."
      />

      <div className="mb-5 flex flex-wrap items-center gap-2">
        {SERIES.map((s) => (
          <button
            key={s.id}
            onClick={() => setSerie(s)}
            aria-pressed={s.id === serie.id}
            className={`num rounded-full border px-3 py-1 text-xs uppercase tracking-wider transition-colors ${
              s.id === serie.id
                ? "border-accent bg-accent text-surface"
                : "border-line text-muted hover:border-accent-2 hover:text-accent-2"
            }`}
          >
            {s.nome}
          </button>
        ))}
        <span className="mx-1 h-4 w-px bg-line" />
        {JANELAS.map((j) => (
          <button
            key={j}
            onClick={() => setUltimos(j)}
            aria-pressed={j === ultimos}
            className={`num rounded-md px-2 py-1 text-xs transition-colors ${
              j === ultimos ? "text-ink underline decoration-accent decoration-2 underline-offset-4" : "text-muted"
            }`}
          >
            {j} pts
          </button>
        ))}
      </div>

      {erro && <ErroBox erro={erro} aoTentar={recarregar} />}

      {!erro && (
        <Card className="overflow-hidden p-5 pt-6">
          <div className="mb-4 flex flex-wrap items-end justify-between gap-4 pl-5">
            {ultimo ? (
              <Kpi
                rotulo={`${serie.nome} · último ponto`}
                valor={Number(ultimo.valor)}
                formato="decimal"
                sufixo={serie.unidade}
                tom="accent-2"
              />
            ) : (
              <div className="h-12" />
            )}
            <div className="flex flex-col items-end gap-1.5">
              <Carimbo fonte="BACEN" cache={dados?.meta?.cache as string | undefined} ms={ms} />
              {ultimo && (
                <span className="num text-xs text-muted">
                  em {formataData(ultimo.data)}
                  {variacao != null && (
                    <span className={variacao >= 0 ? "text-ok" : "text-erro"}>
                      {" "}
                      · {variacao >= 0 ? "▲" : "▼"} {Math.abs(variacao).toLocaleString("pt-BR", { maximumFractionDigits: 2 })} na janela
                    </span>
                  )}
                </span>
              )}
            </div>
          </div>

          {carregando && !dados ? (
            <div className="px-5">
              <Esqueleto linhas={6} />
            </div>
          ) : (
            <EmTransicao ativo={carregando}>
              <SerieChart dados={pontos} cor="var(--color-accent-2)" />
            </EmTransicao>
          )}
        </Card>
      )}
    </div>
  );
}
