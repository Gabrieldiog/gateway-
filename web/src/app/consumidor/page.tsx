"use client";

import { useState } from "react";
import { CadernoHeader } from "@/components/Caderno";
import { Card } from "@/components/Card";
import { Carimbo } from "@/components/Carimbo";
import { SeloFonte } from "@/components/SeloFonte";
import { Termo } from "@/components/Termo";
import { Esqueleto, ErroBox, Vazio, EmTransicao } from "@/components/Estados";
import { useBalcao } from "@/hooks/useBalcao";
import { caminho } from "@/lib/api";
import type { FonteDado, NormalizedResponse, RankingReclamacao } from "@/lib/types";

const TIPOS: [string, string][] = [
  ["bancos", "Bancos e financeiras"],
  ["consorcios", "Consórcios"],
];

const SUGESTOES = ["Nu", "Caixa", "Itaú", "Banco do Brasil", "Mercado Pago"];

function numero(n: number | null): string {
  return n == null ? "—" : n.toLocaleString("pt-BR");
}

function LinhaRanking({ i, maior }: { i: RankingReclamacao; maior: number }) {
  const largura = i.indice != null && maior > 0 ? Math.max(2, (i.indice / maior) * 100) : 0;
  return (
    <li className="py-2">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-0.5">
        <span className="min-w-0 flex-1 truncate text-sm text-ink">
          {i.posicao != null && (
            <span className="num mr-2 inline-block w-6 text-right text-xs text-muted">
              {i.posicao}º
            </span>
          )}
          <span className="font-semibold">{i.instituicao}</span>
        </span>
        <span className="num shrink-0 text-sm font-semibold text-erro">
          {i.indice != null ? i.indice.toLocaleString("pt-BR") : "—"}
        </span>
      </div>
      {i.indice != null && (
        <div className="ml-8 mt-1 h-1.5 overflow-hidden rounded-full bg-surface-2">
          <div className="h-full rounded-full bg-erro/70" style={{ width: `${largura}%` }} />
        </div>
      )}
      <p className="num ml-8 mt-1 flex flex-wrap gap-x-4 text-xs text-muted">
        <span>{numero(i.reclamacoes_procedentes)} procedentes</span>
        <span>{numero(i.reclamacoes_respondidas)} respondidas</span>
        <span>{numero(i.clientes)} clientes</span>
      </p>
    </li>
  );
}

function ResultadoBusca({ tipo, termo }: { tipo: string; termo: string }) {
  const r = useBalcao<NormalizedResponse<RankingReclamacao>>(
    caminho("bacen/reclamacoes", { tipo, busca: termo, limit: 10 }),
  );
  const itens = r.dados?.dados ?? [];

  if (r.erro) return <ErroBox erro={r.erro} aoTentar={r.recarregar} />;
  if (r.carregando && !r.dados) return <Esqueleto linhas={2} />;
  if (!itens.length) {
    return (
      <Vazio>
        nada com “{termo}” — o BC costuma usar o nome do conglomerado (tente “Nu” em vez de
        “Nubank”, “BB” pode ser “Banco do Brasil”).
      </Vazio>
    );
  }
  return (
    <EmTransicao ativo={r.carregando}>
      <div className="flex flex-col gap-3">
        {itens.map((i) => (
          <Card key={i.instituicao} className="p-4">
            <div className="flex flex-wrap items-baseline justify-between gap-x-4">
              <span className="text-sm font-semibold text-ink">{i.instituicao}</span>
              <span className="num text-lg font-semibold text-ink">
                {i.indice != null ? i.indice.toLocaleString("pt-BR") : "sem índice"}
              </span>
            </div>
            <p className="num mt-1 flex flex-wrap gap-x-4 text-xs text-muted">
              {i.top15 ? (
                <span className="text-accent">
                  {i.posicao != null ? `${i.posicao}º no ranking oficial (Top 15)` : "Top 15"}
                </span>
              ) : (
                <span>fora do Top 15 — índice não comparável com os grandes</span>
              )}
              <span>{numero(i.reclamacoes_procedentes)} procedentes</span>
              <span>{numero(i.clientes)} clientes</span>
              <span>{i.periodo}</span>
            </p>
          </Card>
        ))}
      </div>
    </EmTransicao>
  );
}

export default function CadernoConsumidor() {
  const [tipo, setTipo] = useState("bancos");
  const [texto, setTexto] = useState("");
  const [consultado, setConsultado] = useState("");

  const r = useBalcao<NormalizedResponse<RankingReclamacao>>(
    caminho("bacen/reclamacoes", { tipo, grupo: "top15", limit: 15 }),
  );
  const itens = r.dados?.dados ?? [];
  const maior = itens[0]?.indice ?? 0;
  const periodo = itens[0]?.periodo;
  const fonte = r.dados?.meta?.fonte as FonteDado | undefined;

  return (
    <div>
      <CadernoHeader
        numero="XXXII"
        kicker="Banco Central · ranking oficial"
        titulo="Consumidor"
        resumo="Qual banco mais dá dor de cabeça? O Banco Central conta as reclamações que ele mesmo julgou procedentes e divide pelo tamanho de cada instituição. Este é o ranking oficial — e dá pra procurar o seu banco pelo nome."
      />

      <section className="mb-10">
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <h2 className="font-display text-lg font-semibold text-ink">
            O ranking oficial{periodo ? ` · ${periodo}` : ""}
          </h2>
          <div className="inline-flex gap-0.5 rounded-md border border-line p-0.5">
            {TIPOS.map(([v, label]) => (
              <button
                key={v}
                onClick={() => setTipo(v)}
                aria-pressed={tipo === v}
                className={`num rounded px-3 py-1 text-xs uppercase tracking-wider transition-colors ${
                  tipo === v ? "bg-accent/15 font-semibold text-accent" : "text-muted hover:text-ink"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
          <Carimbo fonte="BCB" cache={r.dados?.meta?.cache as string | undefined} ms={r.ms} erro={!!r.erro} />
        </div>
        <p className="mb-4 max-w-2xl font-editorial text-sm leading-relaxed text-ink/75">
          O número é o <Termo t="indicereclamacoes">índice de reclamações</Termo>: quanto maior,
          pior. Só os grandes entram na fila — comparar um banco de 400 clientes com um de 100
          milhões seria maldade estatística.
        </p>
        {r.erro ? (
          <ErroBox erro={r.erro} aoTentar={r.recarregar} />
        ) : r.carregando && !r.dados ? (
          <Esqueleto linhas={8} />
        ) : itens.length ? (
          <EmTransicao ativo={r.carregando}>
            <Card className="p-5">
              <ul className="flex flex-col divide-y divide-line/60">
                {itens.map((i) => (
                  <LinhaRanking key={i.instituicao} i={i} maior={maior} />
                ))}
              </ul>
            </Card>
          </EmTransicao>
        ) : (
          <Vazio>o BC ainda não publicou esse ranking.</Vazio>
        )}
      </section>

      <section>
        <h2 className="mb-1 font-display text-lg font-semibold text-ink">Procure o seu</h2>
        <p className="mb-4 max-w-2xl font-editorial text-sm leading-relaxed text-ink/75">
          Todas as {String(r.dados?.meta?.instituicoes_no_ranking ?? "")} instituições do período
          estão aqui — inclusive as pequenas, que ficam fora do ranking oficial.
        </p>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            setConsultado(texto.trim());
          }}
          className="mb-3 flex flex-wrap gap-2"
        >
          <input
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            placeholder="nome do banco ou financeira"
            aria-label="nome da instituição"
            className="num min-h-9 w-64 max-w-full rounded-md border border-line bg-surface px-3 text-sm text-ink placeholder:text-muted focus:border-accent focus:outline-none"
          />
          <button
            type="submit"
            className="num inline-flex min-h-9 items-center rounded-md border border-line px-3.5 text-xs uppercase tracking-wider text-ink transition-colors hover:bg-surface-2"
          >
            procurar
          </button>
        </form>
        <div className="mb-5 flex flex-wrap items-center gap-2">
          <span className="kicker">experimente:</span>
          {SUGESTOES.map((s) => (
            <button
              key={s}
              onClick={() => {
                setTexto(s);
                setConsultado(s);
              }}
              className="num rounded-full border border-line px-3 py-1 text-xs text-ink transition-colors hover:border-accent hover:text-accent"
            >
              {s}
            </button>
          ))}
        </div>
        {consultado ? (
          <ResultadoBusca tipo={tipo} termo={consultado} />
        ) : (
          <Vazio>digite o nome — ou toque numa sugestão.</Vazio>
        )}
      </section>

      <SeloFonte fonte={fonte} />
    </div>
  );
}
