"use client";

import { useState } from "react";
import { CadernoHeader } from "@/components/Caderno";
import { Card } from "@/components/Card";
import { Carimbo } from "@/components/Carimbo";
import { SeloFonte } from "@/components/SeloFonte";
import { Seletor } from "@/components/Seletor";
import { Esqueleto, ErroBox, Vazio, EmTransicao } from "@/components/Estados";
import { useBalcao } from "@/hooks/useBalcao";
import { caminho } from "@/lib/api";
import type { FonteDado, IndicadorMundial, NormalizedResponse } from "@/lib/types";

const INDICADORES: [string, string][] = [
  ["pib-per-capita", "PIB per capita"],
  ["expectativa-vida", "Expectativa de vida"],
  ["desemprego", "Desemprego"],
  ["inflacao", "Inflação"],
  ["gini", "Desigualdade (Gini)"],
  ["mortalidade-infantil", "Mortalidade infantil"],
  ["internet", "Pessoas na internet"],
  ["co2", "CO₂ per capita"],
];

// nos indicadores de "quanto menos, melhor", a barra maior é a pior notícia
const MENOS_E_MELHOR = new Set(["desemprego", "inflacao", "gini", "mortalidade-infantil", "co2"]);

function formataValor(v: number): string {
  return v.toLocaleString("pt-BR", { maximumFractionDigits: v >= 1000 ? 0 : 2 });
}

function Comparador({ indicador }: { indicador: string }) {
  const r = useBalcao<NormalizedResponse<IndicadorMundial>>(
    caminho("mundo/comparar", { indicador }),
  );
  const itens = r.dados?.dados ?? [];
  const maior = Math.max(...itens.map((i) => i.valor), 0);
  const pior = MENOS_E_MELHOR.has(indicador);

  if (r.erro) return <ErroBox erro={r.erro} aoTentar={r.recarregar} />;
  if (r.carregando && !r.dados) return <Esqueleto linhas={6} />;
  if (!itens.length) return <Vazio>sem medição recente pra esse recorte.</Vazio>;

  return (
    <EmTransicao ativo={r.carregando}>
      <Card className="p-5">
        <p className="kicker mb-3">
          {itens[0].indicador}
          {itens[0].unidade ? ` · ${itens[0].unidade}` : ""}
        </p>
        <ul className="flex flex-col gap-2">
          {itens.map((i) => {
            const brasil = i.iso3 === "BRA";
            return (
              <li key={i.iso3}>
                <div className="flex items-baseline justify-between gap-3">
                  <span className={`text-sm ${brasil ? "font-semibold text-accent" : "text-ink/85"}`}>
                    {i.pais === "Brazil" ? "Brasil" : i.pais}
                    <span className="num ml-1.5 text-[0.65rem] text-muted">({i.ano})</span>
                  </span>
                  <span className={`num text-sm ${brasil ? "font-semibold text-accent" : "text-ink"}`}>
                    {formataValor(i.valor)}
                  </span>
                </div>
                <div className="mt-0.5 h-1.5 overflow-hidden rounded-full bg-surface-2">
                  <div
                    className={`h-full rounded-full ${
                      brasil ? "bg-accent" : pior ? "bg-ocre/50" : "bg-accent-2/50"
                    }`}
                    style={{ width: `${Math.max(2, (i.valor / maior) * 100)}%` }}
                  />
                </div>
              </li>
            );
          })}
        </ul>
        {pior && (
          <p className="num mt-3 text-xs text-muted">neste indicador, barra menor = melhor.</p>
        )}
      </Card>
    </EmTransicao>
  );
}

function EvolucaoBrasil({ indicador }: { indicador: string }) {
  const r = useBalcao<NormalizedResponse<IndicadorMundial>>(
    caminho("mundo/serie", { indicador, ultimos: 25 }),
  );
  const serie = r.dados?.dados ?? [];

  if (r.erro) return <ErroBox erro={r.erro} aoTentar={r.recarregar} />;
  if (r.carregando && !r.dados) return <Esqueleto linhas={3} />;
  if (!serie.length) return <Vazio>sem série pro Brasil nesse indicador.</Vazio>;

  const valores = serie.map((p) => p.valor);
  const min = Math.min(...valores);
  const max = Math.max(...valores);
  const primeiro = serie[0];
  const ultimo = serie[serie.length - 1];

  return (
    <Card className="p-5">
      <p className="kicker mb-2">o Brasil nos últimos {serie.length} anos com medição</p>
      <div className="flex h-20 items-end gap-[2px]">
        {serie.map((p) => (
          <div
            key={p.ano}
            title={`${p.ano}: ${formataValor(p.valor)}`}
            className="min-w-0 flex-1 rounded-t-sm bg-accent-2/50 transition-colors hover:bg-accent-2"
            style={{
              height: `${max === min ? 60 : 12 + ((p.valor - min) / (max - min)) * 88}%`,
            }}
          />
        ))}
      </div>
      <div className="num mt-1.5 flex justify-between text-xs text-muted">
        <span>
          {primeiro.ano} · {formataValor(primeiro.valor)}
        </span>
        <span className="text-ink">
          {ultimo.ano} · {formataValor(ultimo.valor)}
        </span>
      </div>
    </Card>
  );
}

export default function CadernoMundo() {
  const [indicador, setIndicador] = useState("expectativa-vida");

  const painel = useBalcao<NormalizedResponse<IndicadorMundial>>(caminho("mundo/painel"));
  const cartoes = painel.dados?.dados ?? [];
  const fonte = painel.dados?.meta?.fonte as FonteDado | undefined;

  return (
    <div>
      <CadernoHeader
        numero="XXXIV"
        kicker="Banco Mundial · WDI"
        titulo="Brasil no Mundo"
        resumo="Como o país se compara com os vizinhos, os BRICS e os ricos — PIB por pessoa, expectativa de vida, desigualdade, internet e carbono, tudo na mesma régua do Banco Mundial. O ano ao lado de cada número diz de quando é a medição."
      />

      <section className="mb-10">
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <h2 className="font-display text-lg font-semibold text-ink">O retrato do Brasil</h2>
          <Carimbo
            fonte="BANCO MUNDIAL"
            cache={painel.dados?.meta?.cache as string | undefined}
            ms={painel.ms}
            erro={!!painel.erro}
          />
        </div>
        {painel.erro ? (
          <ErroBox erro={painel.erro} aoTentar={painel.recarregar} />
        ) : painel.carregando && !painel.dados ? (
          <Esqueleto linhas={6} />
        ) : cartoes.length ? (
          <EmTransicao ativo={painel.carregando}>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {cartoes.map((c) => (
                <Card key={c.codigo} className="p-4">
                  <p className="kicker">{c.indicador}</p>
                  <p className="num mt-1 text-2xl font-semibold text-ink">
                    {formataValor(c.valor)}
                  </p>
                  <p className="num mt-0.5 text-xs text-muted">
                    {c.unidade} · {c.ano}
                  </p>
                </Card>
              ))}
            </div>
          </EmTransicao>
        ) : (
          <Vazio>o Banco Mundial não respondeu agora.</Vazio>
        )}
      </section>

      <section className="mb-10">
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <h2 className="font-display text-lg font-semibold text-ink">Na mesma régua</h2>
          <Seletor
            value={indicador}
            onChange={(e) => setIndicador(e.target.value)}
            aria-label="indicador"
          >
            {INDICADORES.map(([v, label]) => (
              <option key={v} value={v}>
                {label}
              </option>
            ))}
          </Seletor>
        </div>
        <p className="mb-4 max-w-2xl font-editorial text-sm leading-relaxed text-ink/75">
          Brasil, vizinhos, China, Índia e Estados Unidos — o mesmo indicador, medido do mesmo
          jeito. Cada país publica no seu ritmo; o ano entre parênteses é a medição mais recente.
        </p>
        <Comparador indicador={indicador} />
      </section>

      <section>
        <h2 className="mb-4 font-display text-lg font-semibold text-ink">De onde viemos</h2>
        <EvolucaoBrasil indicador={indicador} />
      </section>

      <SeloFonte fonte={fonte} />
    </div>
  );
}
