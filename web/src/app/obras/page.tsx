"use client";

import { useState } from "react";
import { CadernoHeader } from "@/components/Caderno";
import { Card } from "@/components/Card";
import { Carimbo } from "@/components/Carimbo";
import { LerMais } from "@/components/LerMais";
import { SeloFonte } from "@/components/SeloFonte";
import { Seletor } from "@/components/Seletor";
import { Esqueleto, ErroBox, Vazio, EmTransicao } from "@/components/Estados";
import { useBalcao } from "@/hooks/useBalcao";
import { caminho, formataData, formataReaisCompacto } from "@/lib/api";
import { UFS } from "@/lib/ufs";
import type { EmpenhoObra, FonteDado, NormalizedResponse, ObraPublica } from "@/lib/types";

const SITUACOES: [string, string][] = [
  ["paralisada", "Paralisadas"],
  ["execucao", "Em execução"],
  ["concluida", "Concluídas"],
  ["cadastrada", "Cadastradas"],
];

// o dinheiro que já saiu: os empenhos da obra, abertos sob demanda
function EmpenhosDaObra({ id }: { id: string }) {
  const r = useBalcao<NormalizedResponse<EmpenhoObra>>(caminho("obrasgov/execucao", { id }));
  const empenhos = r.dados?.dados ?? [];
  const totalPagina = r.dados?.meta?.total_empenhado_na_pagina as string | undefined;
  const temProxima = Boolean(r.dados?.meta?.tem_proxima);

  if (r.erro) return <ErroBox erro={r.erro} aoTentar={r.recarregar} />;
  if (r.carregando && !r.dados) return <Esqueleto linhas={2} />;
  if (!empenhos.length) {
    return (
      <p className="font-editorial text-sm italic text-muted">
        nenhum empenho registrado — o dinheiro ainda não começou a sair (ou o órgão não informou).
      </p>
    );
  }
  return (
    <div>
      {totalPagina && Number(totalPagina) > 0 && (
        <p className="kicker mb-2">
          já empenhado:{" "}
          <span className="num normal-case tracking-normal text-ink">
            {formataReaisCompacto(totalPagina)}
            {temProxima && "+"}
          </span>
        </p>
      )}
      <ul className="flex flex-col divide-y divide-line/60">
        {empenhos.map((e, i) => (
          <li key={i} className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-0.5 py-1.5">
            <span className="min-w-0 flex-1 truncate text-sm text-ink/85">
              {e.favorecido ?? "favorecido não informado"}
              {e.nota && <span className="num ml-2 text-xs text-muted">{e.nota}</span>}
            </span>
            <span className="num shrink-0 text-sm text-ink">
              {e.valor ? formataReaisCompacto(e.valor) : "—"}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

// cor do carimbo de situação — parada é vermelho, andando é verde
function corSituacao(s: string | null): string {
  if (s === "Paralisada") return "bg-erro/10 text-erro";
  if (s === "Em execução") return "bg-ok/10 text-ok";
  if (s === "Concluída") return "bg-surface-2 text-muted";
  return "bg-accent-2/10 text-accent-2";
}

export default function CadernoObras() {
  const [situacao, setSituacao] = useState("paralisada");
  const [uf, setUf] = useState("");
  const [pagina, setPagina] = useState(1);
  const [aberta, setAberta] = useState<string | null>(null);

  const r = useBalcao<NormalizedResponse<ObraPublica>>(
    caminho("obrasgov/obras", { situacao, uf: uf || undefined, pagina }),
  );
  const obras = r.dados?.dados ?? [];
  const temProxima = Boolean(r.dados?.meta?.tem_proxima);
  const fonte = r.dados?.meta?.fonte as FonteDado | undefined;

  return (
    <div>
      <CadernoHeader
        numero="XXX"
        kicker="Obrasgov · Ministério da Gestão"
        titulo="Obras Públicas"
        resumo="Toda obra com dinheiro federal, do cadastro oficial — com situação, valores e datas previstas. Comece pelas paralisadas: quando o prazo já passou e a obra parou, o selo de atraso acende sozinho."
      />

      <div className="mb-6 flex flex-wrap items-center gap-3">
        <div className="inline-flex gap-0.5 rounded-md border border-line p-0.5">
          {SITUACOES.map(([v, label]) => (
            <button
              key={v}
              onClick={() => {
                setSituacao(v);
                setPagina(1);
              }}
              aria-pressed={situacao === v}
              className={`num rounded px-3 py-1 text-xs uppercase tracking-wider transition-colors ${
                situacao === v ? "bg-accent/15 font-semibold text-accent" : "text-muted hover:text-ink"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        <Seletor
          value={uf}
          onChange={(e) => {
            setUf(e.target.value);
            setPagina(1);
          }}
          aria-label="estado"
        >
          <option value="">Brasil todo</option>
          {UFS.map((u) => (
            <option key={u}>{u}</option>
          ))}
        </Seletor>
        <Carimbo fonte="OBRASGOV" cache={r.dados?.meta?.cache as string | undefined} ms={r.ms} erro={!!r.erro} />
      </div>

      {r.erro ? (
        <ErroBox erro={r.erro} aoTentar={r.recarregar} />
      ) : r.carregando && !r.dados ? (
        <Esqueleto linhas={8} />
      ) : obras.length ? (
        <EmTransicao ativo={r.carregando}>
          <div className="flex flex-col gap-4">
            {obras.map((o) => (
              <Card key={o.id} className="p-5">
                <div className="mb-1.5 flex flex-wrap items-center gap-2">
                  <span
                    className={`num rounded-full px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wider ${corSituacao(o.situacao)}`}
                  >
                    {o.situacao ?? "sem situação"}
                  </span>
                  {o.atrasada && (
                    <span className="num rounded-full bg-erro px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wider text-white">
                      atrasada
                    </span>
                  )}
                  {o.especie && <span className="num text-xs text-muted">{o.especie}</span>}
                  {o.uf && <span className="num text-xs text-muted">· {o.uf}</span>}
                </div>
                <h3 className="font-display text-lg font-semibold leading-snug text-ink">
                  {o.nome}
                </h3>
                {o.descricao && o.descricao !== o.nome && (
                  <LerMais
                    texto={o.descricao}
                    limite={180}
                    className="mt-1 font-editorial text-sm leading-relaxed text-ink/75"
                  />
                )}
                <div className="num mt-2 flex flex-wrap gap-x-5 gap-y-1 text-xs text-muted">
                  <span className={o.valor_previsto ? "text-ink" : ""}>
                    {o.valor_previsto
                      ? `previsto ${formataReaisCompacto(o.valor_previsto)}`
                      : "valor não informado pela fonte"}
                  </span>
                  {o.inicio_previsto && <span>início previsto {formataData(o.inicio_previsto)}</span>}
                  {o.fim_previsto && (
                    <span className={o.atrasada ? "font-semibold text-erro" : ""}>
                      entrega prevista {formataData(o.fim_previsto)}
                    </span>
                  )}
                  {o.fim_efetivo && <span className="text-ok">entregue em {formataData(o.fim_efetivo)}</span>}
                  {o.executor && <span>executor: {o.executor}</span>}
                  {o.empregos != null && <span>{o.empregos.toLocaleString("pt-BR")} empregos</span>}
                  {o.populacao_beneficiada != null && (
                    <span>{o.populacao_beneficiada.toLocaleString("pt-BR")} beneficiados</span>
                  )}
                  <button
                    onClick={() => setAberta(aberta === o.id ? null : o.id)}
                    aria-expanded={aberta === o.id}
                    className="uppercase tracking-wider text-accent transition-colors hover:text-accent-2"
                  >
                    {aberta === o.id ? "fechar ▴" : "o dinheiro que já saiu ▸"}
                  </button>
                </div>
                {aberta === o.id && (
                  <div className="mt-3 border-t border-line pt-3">
                    <EmpenhosDaObra id={o.id} />
                  </div>
                )}
              </Card>
            ))}
          </div>
          <div className="mt-5 flex items-center gap-3">
            <button
              onClick={() => setPagina((p) => Math.max(1, p - 1))}
              disabled={pagina <= 1}
              className="num inline-flex min-h-9 items-center rounded-md border border-line px-3.5 py-1.5 text-xs uppercase tracking-wider text-ink transition-colors hover:bg-surface-2 disabled:cursor-not-allowed disabled:opacity-40"
            >
              ← anteriores
            </button>
            <span className="num text-xs text-muted">página {pagina}</span>
            <button
              onClick={() => setPagina((p) => p + 1)}
              disabled={!temProxima}
              className="num inline-flex min-h-9 items-center rounded-md border border-line px-3.5 py-1.5 text-xs uppercase tracking-wider text-ink transition-colors hover:bg-surface-2 disabled:cursor-not-allowed disabled:opacity-40"
            >
              próximas →
            </button>
          </div>
        </EmTransicao>
      ) : (
        <Vazio>nenhuma obra com esses filtros.</Vazio>
      )}

      <SeloFonte fonte={fonte} />
    </div>
  );
}
