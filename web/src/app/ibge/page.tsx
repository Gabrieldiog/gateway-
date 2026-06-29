"use client";

import { useState } from "react";
import { CadernoHeader } from "@/components/Caderno";
import { Carimbo } from "@/components/Carimbo";
import { AzulejoGlifo } from "@/components/Azulejo";
import { Esqueleto, ErroBox, Vazio, EmTransicao } from "@/components/Estados";
import { useBalcao } from "@/hooks/useBalcao";
import { caminho } from "@/lib/api";
import { UFS } from "@/lib/ufs";
import type { Estado, Municipio, NormalizedResponse } from "@/lib/types";

type Modo = "estados" | "municipios";

export default function CadernoIbge() {
  const [modo, setModo] = useState<Modo>("estados");
  const [uf, setUf] = useState("SP");

  return (
    <div>
      <CadernoHeader
        numero="V"
        kicker="IBGE · localidades"
        titulo="O território, plano"
        resumo="Estados e municípios do Brasil. Na fonte, a UF de cada município mora três níveis abaixo do aninhamento — o Balcão desce até lá e devolve tudo plano, com sigla e região no primeiro nível."
      />

      <div className="mb-6 flex flex-wrap items-center gap-3">
        <div className="flex gap-1 rounded-md border border-line bg-surface p-1">
          {(["estados", "municipios"] as Modo[]).map((m) => (
            <button
              key={m}
              onClick={() => setModo(m)}
              aria-pressed={m === modo}
              className={`num rounded px-3 py-1 text-xs uppercase tracking-wider transition-colors ${
                m === modo ? "bg-accent text-surface" : "text-muted hover:text-ink"
              }`}
            >
              {m}
            </button>
          ))}
        </div>
        {modo === "municipios" && (
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
        )}
      </div>

      {modo === "estados" ? <Estados /> : <Municipios uf={uf} />}
    </div>
  );
}

function Estados() {
  const { dados, carregando, erro, ms, recarregar } = useBalcao<NormalizedResponse<Estado>>(
    caminho("ibge/estados"),
  );
  const estados = dados?.dados ?? [];

  if (erro) return <ErroBox erro={erro} aoTentar={recarregar} />;
  if (carregando && !dados) return <Esqueleto linhas={6} />;

  return (
    <>
      <div className="mb-3 flex items-center justify-between">
        <p className="kicker">{estados.length} unidades da federação</p>
        <Carimbo fonte="IBGE" cache={dados?.meta?.cache as string | undefined} ms={ms} />
      </div>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
        {estados.map((e) => (
          <article
            key={e.id}
            className="relative rounded-lg border border-line bg-surface p-3"
          >
            <AzulejoGlifo size={12} className="absolute right-2 top-2 text-accent-2/25" />
            <p className="num text-2xl font-semibold text-accent-2">{e.sigla}</p>
            <p className="truncate font-display text-base text-ink">{e.nome}</p>
            <p className="num text-xs text-muted">{e.regiao ?? "—"}</p>
          </article>
        ))}
      </div>
    </>
  );
}

function Municipios({ uf }: { uf: string }) {
  const { dados, carregando, erro, ms, recarregar } = useBalcao<NormalizedResponse<Municipio>>(
    caminho("ibge/municipios", { uf }),
  );
  const municipios = dados?.dados ?? [];

  if (erro) return <ErroBox erro={erro} aoTentar={recarregar} />;
  if (carregando && !dados) return <Esqueleto linhas={6} />;
  if (!municipios.length) return <Vazio>nenhum município encontrado.</Vazio>;

  return (
    <>
      <div className="mb-3 flex items-center justify-between">
        <p className="kicker">
          {municipios.length} municípios · {uf}
        </p>
        <Carimbo fonte="IBGE" cache={dados?.meta?.cache as string | undefined} ms={ms} />
      </div>
      <EmTransicao ativo={carregando}>
        <div className="columns-2 gap-3 sm:columns-3 lg:columns-4">
          {municipios.map((m) => (
            <div
              key={m.id}
              className="mb-1.5 flex items-baseline justify-between gap-2 break-inside-avoid rounded-md border border-line bg-surface px-3 py-1.5"
            >
              <span className="truncate text-sm text-ink" title={m.nome}>
                {m.nome}
              </span>
              <span className="num shrink-0 text-[0.65rem] text-muted">{m.regiao ?? ""}</span>
            </div>
          ))}
        </div>
      </EmTransicao>
    </>
  );
}
