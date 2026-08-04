"use client";

import { CadernoHeader } from "@/components/Caderno";
import { Card } from "@/components/Card";
import { Carimbo } from "@/components/Carimbo";
import { SeloFonte } from "@/components/SeloFonte";
import { Termo } from "@/components/Termo";
import { Esqueleto, ErroBox, Vazio, EmTransicao } from "@/components/Estados";
import { useBalcao } from "@/hooks/useBalcao";
import { caminho } from "@/lib/api";
import type { FonteDado, IndicadorTrabalho, NormalizedResponse } from "@/lib/types";

function reais(v: number | null): string {
  return v == null ? "sem dado" : `R$ ${Math.round(v).toLocaleString("pt-BR")}`;
}

// mini gráfico de linha da série; devolve o caminho SVG normalizado
function Linha({ serie }: { serie: IndicadorTrabalho[] }) {
  const vals = serie.map((p) => p.valor ?? 0);
  if (vals.length < 2) return null;
  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const faixa = max - min || 1;
  const pontos = vals.map((v, i) => {
    const x = (i / (vals.length - 1)) * 100;
    const y = 100 - ((v - min) / faixa) * 88 - 6;
    return `${x},${y}`;
  });
  return (
    <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="mt-3 h-16 w-full">
      <polyline
        points={pontos.join(" ")}
        fill="none"
        stroke="currentColor"
        strokeWidth="2.5"
        vectorEffect="non-scaling-stroke"
        className="text-accent-2"
      />
    </svg>
  );
}

function IndicadorNacional({
  titulo,
  url,
  termo,
  formata,
  tom,
}: {
  titulo: React.ReactNode;
  url: string;
  termo?: React.ReactNode;
  formata: (v: number | null) => string;
  tom: string;
}) {
  const r = useBalcao<NormalizedResponse<IndicadorTrabalho>>(url);
  const serie = r.dados?.dados ?? [];
  const atual = serie[serie.length - 1];
  const anterior = serie[serie.length - 2];
  const delta = atual?.valor != null && anterior?.valor != null ? atual.valor - anterior.valor : null;

  if (r.erro) return <ErroBox erro={r.erro} aoTentar={r.recarregar} />;
  if (r.carregando && !r.dados) return <Esqueleto linhas={4} />;
  if (!atual) return <Vazio>o IBGE não respondeu agora.</Vazio>;

  return (
    <Card className="p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-x-2 gap-y-1">
        <p className="kicker">{titulo}</p>
        <Carimbo fonte="IBGE" cache={r.dados?.meta?.cache as string | undefined} ms={r.ms} erro={false} />
      </div>
      <p className={`num mt-1 font-display text-4xl font-semibold ${tom}`}>{formata(atual.valor)}</p>
      <p className="num mt-0.5 text-xs text-muted">
        {atual.periodo}
        {delta != null && (
          <span className={delta > 0 ? "ml-2 text-erro" : delta < 0 ? "ml-2 text-ok" : "ml-2"}>
            {delta > 0 ? "▲" : delta < 0 ? "▼" : "="} {Math.abs(delta).toLocaleString("pt-BR")}
            {atual.unidade === "%" ? " p.p." : ""} vs. o trimestre anterior
          </span>
        )}
      </p>
      <div className={tom}>
        <Linha serie={serie} />
      </div>
      {termo && <p className="mt-1 font-editorial text-xs text-muted">{termo}</p>}
    </Card>
  );
}

function DesempregoPorUf() {
  const r = useBalcao<NormalizedResponse<IndicadorTrabalho>>(
    caminho("sidra/desemprego", { por: "uf" }),
  );
  const itens = r.dados?.dados ?? [];
  const maior = itens[0]?.valor ?? 0;

  if (r.erro) return <ErroBox erro={r.erro} aoTentar={r.recarregar} />;
  if (r.carregando && !r.dados) return <Esqueleto linhas={8} />;
  if (!itens.length) return <Vazio>sem dados por estado agora.</Vazio>;

  return (
    <EmTransicao ativo={r.carregando}>
      <p className="mb-3 font-editorial text-sm text-muted">
        {r.dados?.meta?.periodo as string} · do estado que mais sofre ao que menos sofre
      </p>
      <Card className="p-5">
        <ul className="grid gap-x-8 gap-y-2 sm:grid-cols-2">
          {itens.map((i) => (
            <li key={i.uf}>
              <div className="flex items-baseline justify-between gap-2">
                <span className="text-sm text-ink">
                  <span className="num mr-2 inline-block w-8 font-semibold">{i.uf}</span>
                  <span className="text-muted">{i.local}</span>
                </span>
                <span className="num text-sm font-semibold text-ink">
                  {i.valor?.toLocaleString("pt-BR")}%
                </span>
              </div>
              <div className="mt-0.5 h-1.5 overflow-hidden rounded-full bg-surface-2">
                <div
                  className="h-full rounded-full bg-ocre/60"
                  style={{ width: `${maior ? Math.max(3, ((i.valor ?? 0) / maior) * 100) : 0}%` }}
                />
              </div>
            </li>
          ))}
        </ul>
      </Card>
      <SeloFonte fonte={r.dados?.meta?.fonte as FonteDado | undefined} />
    </EmTransicao>
  );
}

export default function CadernoTrabalho() {
  // mesmo endpoint do primeiro IndicadorNacional; o cache do gateway dedup a
  // chamada, então isto só serve pra ler o trimestre e datar o selo de frescor
  const r = useBalcao<NormalizedResponse<IndicadorTrabalho>>(
    caminho("sidra/desemprego", { ultimos: 8 }),
  );
  const serie = r.dados?.dados ?? [];
  const periodo = serie[serie.length - 1]?.periodo;

  return (
    <div>
      <CadernoHeader
        numero="XXXVII"
        kicker="IBGE · PNAD Contínua"
        titulo="Trabalho e Renda"
        resumo="O retrato oficial do mercado de trabalho: quantos estão sem emprego e quanto ganha quem trabalha, medido pela PNAD Contínua do IBGE. Os trimestres são móveis, cada leitura anda um mês."
        referencia={periodo || undefined}
      />

      <section className="mb-10 grid gap-4 sm:grid-cols-2">
        <IndicadorNacional
          titulo={<Termo t="desocupacao">Desemprego</Termo>}
          url={caminho("sidra/desemprego", { ultimos: 8 })}
          formata={(v) => (v == null ? "sem dado" : `${v.toLocaleString("pt-BR")}%`)}
          tom="text-ink"
          termo="taxa de desocupação, pessoas de 14 anos ou mais"
        />
        <IndicadorNacional
          titulo={<Termo t="rendimentoreal">Renda média</Termo>}
          url={caminho("sidra/rendimento", { ultimos: 8 })}
          formata={reais}
          tom="text-ink"
          termo="rendimento médio real do trabalho, a preços de hoje"
        />
      </section>

      <section>
        <h2 className="mb-4 font-display text-lg font-semibold text-ink">O desemprego pelo país</h2>
        <DesempregoPorUf />
      </section>
    </div>
  );
}
