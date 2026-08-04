"use client";

/* eslint-disable @next/next/no-img-element */
import { useState } from "react";
import { CadernoHeader } from "@/components/Caderno";
import { Carimbo } from "@/components/Carimbo";
import { AzulejoGlifo } from "@/components/Azulejo";
import { Seletor } from "@/components/Seletor";
import { SeloFonte } from "@/components/SeloFonte";
import { Esqueleto, ErroBox, Vazio } from "@/components/Estados";
import { useBalcao } from "@/hooks/useBalcao";
import { caminho } from "@/lib/api";
import { UFS } from "@/lib/ufs";
import type { NormalizedResponse, Senador } from "@/lib/types";

const FONTE_SENADO = {
  nome: "Senado Federal, Dados Abertos Legislativos",
  url: "https://legis.senado.leg.br/dadosabertos/",
  nota: "Lista oficial de senadores em exercício, direto da API do Senado. O Balcão pede JSON, desembrulha o envelope triplo e aplica os filtros de UF e partido.",
};

export default function CadernoSenado() {
  const [uf, setUf] = useState("");
  const [partido, setPartido] = useState("");
  const url = caminho("senado/senadores", { uf: uf || undefined, partido: partido || undefined });
  const { dados, carregando, erro, ms, recarregar } = useBalcao<NormalizedResponse<Senador>>(url);
  const senadores = dados?.dados ?? [];

  return (
    <div>
      <CadernoHeader
        numero="III"
        kicker="Senado Federal"
        titulo="O plenário dos estados"
        resumo="Os senadores em exercício. A fonte responde XML por padrão e não filtra a lista; o Balcão pede JSON, desembrulha o envelope triplo e aplica o recorte por UF e partido aqui no gateway."
      />

      <div className="mb-6 flex flex-wrap items-center gap-3">
        <label className="num flex items-center gap-2 text-xs uppercase tracking-wider text-muted">
          UF
          <Seletor value={uf} onChange={(e) => setUf(e.target.value)}>
            <option value="">todas</option>
            {UFS.map((u) => (
              <option key={u} value={u}>
                {u}
              </option>
            ))}
          </Seletor>
        </label>
        <label className="num flex items-center gap-2 text-xs uppercase tracking-wider text-muted">
          Partido
          <input
            value={partido}
            onChange={(e) => setPartido(e.target.value.toUpperCase())}
            placeholder="todos"
            className="w-24 rounded-md border border-line bg-surface px-2 py-1 uppercase text-ink placeholder:normal-case placeholder:text-muted"
          />
        </label>
        <span className="num ml-auto flex items-center gap-3 text-xs text-muted">
          {!carregando && dados && <span>{senadores.length} senadores</span>}
          <Carimbo fonte="SENADO" cache={dados?.meta?.cache as string | undefined} ms={ms} erro={!!erro} />
        </span>
      </div>

      {erro ? (
        <ErroBox erro={erro} aoTentar={recarregar} />
      ) : carregando && !dados ? (
        <Esqueleto linhas={6} />
      ) : senadores.length === 0 ? (
        <Vazio>nenhum senador para esse filtro.</Vazio>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {senadores.map((s) => (
            <article
              key={s.id}
              className="relative flex gap-3 rounded-lg border border-line bg-surface p-3"
            >
              <AzulejoGlifo size={12} className="absolute left-1.5 top-1.5 text-accent-2/30" />
              <span className="h-16 w-13 shrink-0 overflow-hidden rounded-sm border border-line bg-surface-2">
                {s.foto && <img src={s.foto} alt="" loading="lazy" className="h-full w-full object-cover" />}
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate font-display text-lg leading-tight text-ink">{s.nome}</p>
                <p className="num text-xs text-muted">
                  {[s.partido, s.uf].filter(Boolean).join(" · ") || "sem dado"}
                </p>
                {s.email && (
                  <p className="mt-1 truncate text-xs text-accent-2" title={s.email}>
                    {s.email}
                  </p>
                )}
              </div>
            </article>
          ))}
        </div>
      )}

      <SeloFonte fonte={FONTE_SENADO} />
    </div>
  );
}
