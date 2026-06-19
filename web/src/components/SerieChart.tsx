"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formataData } from "@/lib/api";

interface Ponto {
  rotulo: string;
  data: string | null;
  valor: number;
}

// objetos estáveis fora do componente: o Recharts compara por referência
const MARGEM = { top: 16, right: 16, bottom: 4, left: 4 };
const TICK = { fontSize: 11, fontFamily: "var(--font-mono)", fill: "var(--color-muted)" };
const CURSOR = { stroke: "var(--color-accent)", strokeWidth: 1 };

function CustomTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: Ponto }> }) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  return (
    <div className="rounded-md border border-ink/20 bg-surface px-3 py-2 shadow-sm">
      <p className="num text-xs text-muted">{formataData(p.data)}</p>
      <p className="num text-base font-semibold text-ink">
        {p.valor.toLocaleString("pt-BR", { maximumFractionDigits: 4 })}
      </p>
    </div>
  );
}

// aceita qualquer ponto com data + valor (PontoSerie do BACEN ou PontoIpea)
export function SerieChart({
  dados,
  cor = "var(--color-accent-2)",
}: {
  dados: { data: string | null; valor: number | string | null }[];
  cor?: string;
}) {
  const pontos: Ponto[] = dados.map((d) => ({
    rotulo: d.data ? formataData(d.data).slice(0, 5) : "",
    data: d.data,
    valor: Number(d.valor),
  }));
  const ultimo = pontos[pontos.length - 1];

  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={pontos} margin={MARGEM}>
          <defs>
            <linearGradient id="fillSerie" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={cor} stopOpacity={0.18} />
              <stop offset="100%" stopColor={cor} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid
            horizontal
            vertical={false}
            strokeDasharray="2 4"
            stroke="var(--color-muted)"
            strokeOpacity={0.3}
          />
          <XAxis
            dataKey="rotulo"
            tick={TICK}
            tickLine={false}
            axisLine={{ stroke: "var(--color-line)" }}
            minTickGap={24}
          />
          <YAxis
            orientation="right"
            tick={TICK}
            tickLine={false}
            axisLine={false}
            width={48}
            domain={["auto", "auto"]}
          />
          <Tooltip content={<CustomTooltip />} cursor={CURSOR} />
          {ultimo && (
            <ReferenceLine
              x={ultimo.rotulo}
              stroke="var(--color-accent)"
              strokeOpacity={0.5}
              strokeDasharray="3 3"
            />
          )}
          <Area
            type="monotone"
            dataKey="valor"
            stroke={cor}
            strokeWidth={2.5}
            fill="url(#fillSerie)"
            dot={false}
            activeDot={{ r: 4, fill: cor, stroke: "var(--color-surface)", strokeWidth: 2 }}
            animationDuration={500}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
