"use client";

import { useState } from "react";
import { CadernoHeader } from "@/components/Caderno";
import { Card } from "@/components/Card";
import { Carimbo } from "@/components/Carimbo";
import { Esqueleto, ErroBox, Vazio, EmTransicao } from "@/components/Estados";
import { useBalcao } from "@/hooks/useBalcao";
import { caminho } from "@/lib/api";
import type { IndicadorAgro, NormalizedResponse } from "@/lib/types";

const PRODUTOS: [string, string][] = [
  ["soja", "soja"], ["milho", "milho"], ["cana", "cana-de-açúcar"], ["algodao", "algodão"],
  ["arroz", "arroz"], ["feijao", "feijão"], ["trigo", "trigo"], ["mandioca", "mandioca"],
];
const ANIMAIS: [string, string][] = [
  ["bovino", "bovino"], ["suino", "suíno"], ["galinaceos", "galináceos"], ["equino", "equino"],
  ["caprino", "caprino"], ["ovino", "ovino"], ["bubalino", "bubalino"], ["codorna", "codorna"],
];
const VARIAVEIS: [string, string][] = [["quantidade", "quantidade"], ["area", "área plantada"]];
const ANOS = [2023, 2022, 2021, 2020];

function compacto(valor: number, unidade: string | null): string {
  const n = new Intl.NumberFormat("pt-BR", { notation: "compact", maximumFractionDigits: 1 }).format(valor);
  const u =
    unidade === "Toneladas" ? "t" : unidade === "Hectares" ? "ha" : unidade === "Cabeças" ? "cab." : unidade ?? "";
  return `${n} ${u}`.trim();
}

export default function CadernoAgro() {
  const [modo, setModo] = useState<"producao" | "rebanho">("producao");
  const [produto, setProduto] = useState("soja");
  const [animal, setAnimal] = useState("bovino");
  const [variavel, setVariavel] = useState("quantidade");
  const [ano, setAno] = useState(2023);

  const url =
    modo === "producao"
      ? caminho("sidra/producao", { produto, variavel, ano })
      : caminho("sidra/rebanho", { animal, ano });
  const lista = useBalcao<NormalizedResponse<IndicadorAgro>>(url);

  const dados = (lista.dados?.dados ?? []).filter((d) => d.valor != null);
  const max = dados[0]?.valor ?? 1; // o conector já devolve ordenado desc
  const total = dados.reduce((s, d) => s + (d.valor ?? 0), 0);
  const unidade = dados[0]?.unidade ?? null;
  const lider = dados[0];
  const oque = modo === "producao" ? PRODUTOS.find((p) => p[0] === produto)?.[1] : ANIMAIS.find((a) => a[0] === animal)?.[1];

  return (
    <div>
      <CadernoHeader
        numero="IX"
        kicker="IBGE SIDRA · agro"
        titulo="O agro, por estado"
        resumo="Quanto cada estado produz e cria, da Produção Agrícola Municipal e da Pesquisa da Pecuária do IBGE. Escolha a cultura ou o rebanho e veja o ranking — o SIDRA fala em código, o Balcão devolve limpo."
      />

      <div className="mb-6 flex flex-wrap items-center gap-4">
        <div className="flex gap-1 rounded-md border border-line bg-surface p-0.5">
          {(["producao", "rebanho"] as const).map((m) => (
            <button
              key={m}
              onClick={() => setModo(m)}
              aria-pressed={m === modo}
              className={`num rounded px-3 py-1 text-xs uppercase tracking-wider transition-colors ${
                m === modo ? "bg-accent/10 text-accent" : "text-muted hover:text-ink"
              }`}
            >
              {m === "producao" ? "lavoura" : "rebanho"}
            </button>
          ))}
        </div>

        {modo === "producao" ? (
          <>
            <Seletor rotulo="Cultura" valor={produto} aoMudar={setProduto} opcoes={PRODUTOS} />
            <Seletor rotulo="Medida" valor={variavel} aoMudar={setVariavel} opcoes={VARIAVEIS} />
          </>
        ) : (
          <Seletor rotulo="Rebanho" valor={animal} aoMudar={setAnimal} opcoes={ANIMAIS} />
        )}

        <div className="flex gap-1">
          {ANOS.map((a) => (
            <button
              key={a}
              onClick={() => setAno(a)}
              aria-pressed={a === ano}
              className={`num rounded px-1.5 py-0.5 text-xs transition-colors ${
                a === ano ? "text-ink underline decoration-accent decoration-2 underline-offset-4" : "text-muted"
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
              {modo === "producao" ? "Produção de" : "Rebanho de"} {oque} · {ano}
            </h2>
            <p className="num text-xs text-muted">
              {lista.carregando && !lista.dados ? "consultando…" : `${dados.length} estados com dado`}
            </p>
          </div>
          <Carimbo
            fonte="SIDRA"
            cache={lista.dados?.meta?.cache as string | undefined}
            ms={lista.ms}
            erro={!!lista.erro}
          />
        </div>

        <div className="my-5 pl-5">
          {lista.erro ? (
            <ErroBox erro={lista.erro} aoTentar={lista.recarregar} />
          ) : lista.carregando && !lista.dados ? (
            <Esqueleto linhas={6} />
          ) : dados.length === 0 ? (
            <Vazio>sem dado para essa combinação.</Vazio>
          ) : (
            <EmTransicao ativo={lista.carregando}>
              <div className="mb-6 flex flex-wrap gap-8">
                <div className="flex flex-col">
                  <span className="kicker mb-1">Total Brasil</span>
                  <span className="font-display text-4xl font-semibold leading-none tracking-tight text-accent-2 sm:text-5xl">
                    {compacto(total, unidade)}
                  </span>
                </div>
                {lider && (
                  <div className="flex flex-col">
                    <span className="kicker mb-1">Líder</span>
                    <span className="font-display text-4xl font-semibold leading-none tracking-tight text-ink sm:text-5xl">
                      {lider.localidade}
                    </span>
                    <span className="num mt-1 text-sm text-accent">{compacto(lider.valor ?? 0, unidade)}</span>
                  </div>
                )}
              </div>

              <ul className="flex flex-col gap-2.5">
                {dados.slice(0, 15).map((d, i) => (
                  <li key={d.localidade_id ?? d.localidade}>
                    <div className="mb-1 flex items-baseline justify-between gap-3">
                      <span className="truncate text-sm text-ink/85">{d.localidade}</span>
                      <span className={`num shrink-0 text-sm ${i === 0 ? "text-accent" : "text-ink"}`}>
                        {compacto(d.valor ?? 0, d.unidade)}
                      </span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-sm bg-surface-2">
                      <div
                        className={`h-full rounded-sm ${i === 0 ? "bg-accent" : "bg-accent-2/70"}`}
                        style={{ width: `${Math.max(((d.valor ?? 0) / max) * 100, 1.5)}%` }}
                      />
                    </div>
                  </li>
                ))}
              </ul>
            </EmTransicao>
          )}
        </div>
      </Card>
    </div>
  );
}

function Seletor({
  rotulo,
  valor,
  aoMudar,
  opcoes,
}: {
  rotulo: string;
  valor: string;
  aoMudar: (v: string) => void;
  opcoes: [string, string][];
}) {
  return (
    <label className="num flex items-center gap-2 text-xs uppercase tracking-wider text-muted">
      {rotulo}
      <select
        value={valor}
        onChange={(e) => aoMudar(e.target.value)}
        className="rounded-md border border-line bg-surface px-2 py-1 text-ink"
      >
        {opcoes.map(([v, nome]) => (
          <option key={v} value={v}>
            {nome}
          </option>
        ))}
      </select>
    </label>
  );
}
