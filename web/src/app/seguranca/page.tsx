"use client";

import { useState } from "react";
import { CadernoHeader } from "@/components/Caderno";
import { Card } from "@/components/Card";
import { Carimbo } from "@/components/Carimbo";
import { SeloFonte } from "@/components/SeloFonte";
import { Seletor } from "@/components/Seletor";
import { Termo } from "@/components/Termo";
import { Esqueleto, ErroBox, Vazio, EmTransicao } from "@/components/Estados";
import { useBalcao } from "@/hooks/useBalcao";
import { caminho } from "@/lib/api";
import { UFS } from "@/lib/ufs";
import type { FonteDado, NormalizedResponse, OcorrenciaSeguranca } from "@/lib/types";

const CRIMES: [string, string][] = [
  ["homicidio", "Homicídio doloso"],
  ["feminicidio", "Feminicídio"],
  ["latrocinio", "Latrocínio"],
  ["estupro", "Estupro"],
  ["roubo-veiculo", "Roubo de veículo"],
  ["furto-veiculo", "Furto de veículo"],
  ["trafico", "Tráfico de drogas"],
  ["desaparecida", "Pessoa desaparecida"],
];

const ANOS = Array.from({ length: 2025 - 2015 + 1 }, (_, i) => String(2025 - i));

function inteiro(v: number): string {
  return v.toLocaleString("pt-BR");
}

function PanoramaEstado({ uf, ano }: { uf: string; ano: string }) {
  const r = useBalcao<NormalizedResponse<OcorrenciaSeguranca>>(
    caminho("seguranca/panorama", { uf, ano }),
  );
  const itens = r.dados?.dados ?? [];
  const maior = Math.max(...itens.map((i) => i.total), 0);

  if (r.erro) return <ErroBox erro={r.erro} aoTentar={r.recarregar} />;
  if (r.carregando && !r.dados) return <Esqueleto linhas={8} />;
  if (!itens.length) return <Vazio>o Sinesp não tem registro desse estado nesse ano.</Vazio>;

  return (
    <EmTransicao ativo={r.carregando}>
      <Card className="p-5">
        <ul className="flex flex-col gap-2.5">
          {itens.map((i) => (
            <li key={i.evento}>
              <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-0.5">
                <span className="min-w-0 flex-1 truncate text-sm text-ink">{i.evento}</span>
                {i.feminino != null && i.masculino != null && (
                  <span className="num text-xs text-muted">
                    <span className="text-accent-2">♀ {inteiro(i.feminino)}</span> ·{" "}
                    <span>♂ {inteiro(i.masculino)}</span>
                  </span>
                )}
                <span className="num shrink-0 text-sm font-semibold text-ink">{inteiro(i.total)}</span>
              </div>
              <div className="mt-0.5 h-1.5 overflow-hidden rounded-full bg-surface-2">
                <div
                  className="h-full rounded-full bg-erro/55"
                  style={{ width: `${maior ? Math.max(2, (i.total / maior) * 100) : 0}%` }}
                />
              </div>
            </li>
          ))}
        </ul>
        <p className="num mt-3 border-t border-line pt-2 text-xs text-muted">
          nos crimes contra a pessoa, ♀/♂ é o sexo das vítimas.
        </p>
      </Card>
    </EmTransicao>
  );
}

function RankingEstados({ ano, ufDestaque }: { ano: string; ufDestaque: string }) {
  const [crime, setCrime] = useState("homicidio");
  const r = useBalcao<NormalizedResponse<OcorrenciaSeguranca>>(
    caminho("seguranca/ranking", { crime, ano }),
  );
  const itens = r.dados?.dados ?? [];
  const maior = itens[0]?.por_100k ?? 0;

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <Seletor value={crime} onChange={(e) => setCrime(e.target.value)} aria-label="crime">
          {CRIMES.map(([v, label]) => (
            <option key={v} value={v}>
              {label}
            </option>
          ))}
        </Seletor>
        <span className="kicker">
          por <Termo t="por100k">100 mil habitantes</Termo>
        </span>
      </div>
      {r.erro ? (
        <ErroBox erro={r.erro} aoTentar={r.recarregar} />
      ) : r.carregando && !r.dados ? (
        <Esqueleto linhas={8} />
      ) : itens.length ? (
        <EmTransicao ativo={r.carregando}>
          <Card className="p-5">
            <ul className="grid gap-x-8 gap-y-2 sm:grid-cols-2">
              {itens.map((i, pos) => {
                const meu = i.uf === ufDestaque;
                return (
                  <li key={i.uf}>
                    <div className="flex items-baseline justify-between gap-2">
                      <span className={`text-sm ${meu ? "font-semibold text-accent" : "text-ink"}`}>
                        <span className="num mr-1.5 inline-block w-5 text-right text-xs text-muted">
                          {pos + 1}
                        </span>
                        {i.uf} <span className="text-muted">{i.local}</span>
                      </span>
                      <span className={`num text-sm font-semibold ${meu ? "text-accent" : "text-ink"}`}>
                        {i.por_100k?.toLocaleString("pt-BR")}
                      </span>
                    </div>
                    <div className="mt-0.5 h-1.5 overflow-hidden rounded-full bg-surface-2">
                      <div
                        className={`h-full rounded-full ${meu ? "bg-accent" : "bg-erro/50"}`}
                        style={{ width: `${maior ? Math.max(2, ((i.por_100k ?? 0) / maior) * 100) : 0}%` }}
                      />
                    </div>
                  </li>
                );
              })}
            </ul>
          </Card>
          <SeloFonte fonte={r.dados?.meta?.fonte as FonteDado | undefined} />
        </EmTransicao>
      ) : (
        <Vazio>sem dados desse crime nesse ano.</Vazio>
      )}
    </div>
  );
}

export default function CadernoSeguranca() {
  const [uf, setUf] = useState("SP");
  const [ano, setAno] = useState("2025");

  const r = useBalcao<NormalizedResponse<OcorrenciaSeguranca>>(
    caminho("seguranca/panorama", { uf, ano }),
  );

  return (
    <div>
      <CadernoHeader
        numero="XXXVIII"
        kicker="Sinesp · Ministério da Justiça"
        titulo="Segurança"
        resumo="As ocorrências criminais que as polícias estaduais informam ao Ministério da Justiça, estado por estado. Cada UF registra do seu jeito, então a comparação tem ressalvas — por isso o ranking entre estados é sempre por 100 mil habitantes."
        referencia={`ano-base ${ano}`}
      />

      <div className="mb-6 flex flex-wrap items-center gap-3">
        <Seletor value={uf} onChange={(e) => setUf(e.target.value)} aria-label="estado">
          {UFS.map((u) => (
            <option key={u}>{u}</option>
          ))}
        </Seletor>
        <Seletor value={ano} onChange={(e) => setAno(e.target.value)} aria-label="ano">
          {ANOS.map((a) => (
            <option key={a}>{a}</option>
          ))}
        </Seletor>
        <Carimbo fonte="SINESP" cache={r.dados?.meta?.cache as string | undefined} ms={r.ms} erro={!!r.erro} />
      </div>

      <section className="mb-10">
        <h2 className="mb-4 font-display text-lg font-semibold text-ink">
          No estado ({uf}, {ano})
        </h2>
        <PanoramaEstado uf={uf} ano={ano} />
      </section>

      <section>
        <h2 className="mb-1 font-display text-lg font-semibold text-ink">Entre os estados</h2>
        <p className="mb-4 max-w-2xl font-editorial text-sm leading-relaxed text-ink/75">
          O mesmo crime nos 27 estados, do que mais sofre ao que menos sofre — {uf} aparece
          destacado. Sempre por 100 mil habitantes, pra não confundir tamanho com risco.
        </p>
        <RankingEstados ano={ano} ufDestaque={uf} />
      </section>
    </div>
  );
}
