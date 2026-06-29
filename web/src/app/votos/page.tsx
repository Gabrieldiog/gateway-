"use client";

import { useEffect, useState } from "react";
import { CadernoHeader } from "@/components/Caderno";
import { Card } from "@/components/Card";
import { Carimbo } from "@/components/Carimbo";
import { Esqueleto, ErroBox, Vazio, EmTransicao } from "@/components/Estados";
import { useBalcao } from "@/hooks/useBalcao";
import { caminho, formataData } from "@/lib/api";
import type {
  NormalizedResponse,
  Votacao,
  VotoDeputado,
  VotosDeputadoOut,
} from "@/lib/types";

// ordem e cor de cada tipo de voto
const ORDEM = ["Sim", "Não", "Abstenção", "Obstrução"];
const COR_VOTO: Record<string, { txt: string; bar: string }> = {
  Sim: { txt: "text-ok", bar: "bg-ok" },
  Não: { txt: "text-accent", bar: "bg-accent" },
  Abstenção: { txt: "text-muted", bar: "bg-muted" },
  Obstrução: { txt: "text-ocre", bar: "bg-ocre" },
};
function corVoto(v: string) {
  return COR_VOTO[v] ?? { txt: "text-ink", bar: "bg-ink/70" };
}

type Modo = "votacao" | "deputado";

export default function CadernoVotos() {
  const [modo, setModo] = useState<Modo>("votacao");

  return (
    <div>
      <CadernoHeader
        numero="VIII"
        kicker="Câmara dos Deputados"
        titulo="Como cada deputado votou"
        resumo="Duas lentes sobre o mesmo plenário: por votação, o voto de todos num projeto; por deputado, como o seu candidato votou nas votações recentes. Votações simbólicas (de viva voz) não registram voto individual."
      />

      <div className="mb-6 flex w-fit gap-1 rounded-md border border-line bg-surface p-1">
        {(["votacao", "deputado"] as Modo[]).map((m) => (
          <button
            key={m}
            onClick={() => setModo(m)}
            aria-pressed={m === modo}
            className={`num rounded px-3 py-1.5 text-xs uppercase tracking-wider transition-colors ${
              m === modo ? "bg-accent text-surface" : "text-muted hover:text-ink"
            }`}
          >
            {m === "votacao" ? "por votação" : "por deputado"}
          </button>
        ))}
      </div>

      {modo === "votacao" ? <PorVotacao /> : <PorDeputado />}
    </div>
  );
}

// limite de votações que o auto-avanço percorre procurando uma nominal
const CAP = 12;

function PorVotacao() {
  const lista = useBalcao<NormalizedResponse<Votacao>>(
    caminho("camara/votacoes", { orgao: 180, itens: 25 }),
  );
  const votacoes = lista.dados?.dados ?? [];

  const [idx, setIdx] = useState(0);
  const [manual, setManual] = useState(false);
  const [filtro, setFiltro] = useState<string | null>(null);

  const sel = votacoes[idx] ?? null;
  const votos = useBalcao<NormalizedResponse<VotoDeputado>>(
    sel ? caminho(`camara/votacoes/${sel.id}/votos`) : null,
  );
  const deputados = votos.dados?.dados ?? [];
  const placar = votos.dados?.meta?.placar as Record<string, number> | undefined;
  const aviso = votos.dados?.meta?.aviso as string | undefined;

  // votação simbólica vem vazia e leve: enquanto ninguém escolheu na mão,
  // pula pra próxima até achar uma nominal (que registra voto por deputado).
  useEffect(() => {
    if (
      !manual &&
      votos.dados &&
      deputados.length === 0 &&
      idx < Math.min(votacoes.length, CAP) - 1
    ) {
      setIdx((i) => i + 1);
    }
  }, [votos.dados, deputados.length, manual, idx, votacoes.length]);

  const filtrados = (filtro ? deputados.filter((d) => d.voto === filtro) : deputados)
    .slice()
    .sort((a, b) => (a.partido ?? "").localeCompare(b.partido ?? "") || a.deputado.localeCompare(b.deputado));

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_1.3fr]">
      {/* lista de votações */}
      <div>
        <p className="kicker mb-3">Plenário · votações recentes</p>
        {lista.erro ? (
          <ErroBox erro={lista.erro} aoTentar={lista.recarregar} />
        ) : lista.carregando && !lista.dados ? (
          <Esqueleto linhas={8} />
        ) : votacoes.length === 0 ? (
          <Vazio>nenhuma votação encontrada.</Vazio>
        ) : (
          <ul className="flex max-h-160 flex-col gap-1 overflow-y-auto pr-1">
            {votacoes.map((v, i) => {
              const ativo = i === idx;
              return (
                <li key={v.id}>
                  <button
                    onClick={() => {
                      setIdx(i);
                      setManual(true);
                      setFiltro(null);
                    }}
                    className={`flex w-full flex-col gap-0.5 rounded-md border px-3 py-2 text-left transition-colors ${
                      ativo ? "border-accent/40 bg-surface" : "border-transparent hover:bg-surface/70"
                    }`}
                  >
                    <span className="line-clamp-2 text-sm text-ink/90">{v.descricao}</span>
                    <span className="num text-xs text-muted">
                      {v.data ?? "—"}
                      {v.aprovada != null && (
                        <span className={v.aprovada ? "text-ok" : "text-accent"}>
                          {" "}
                          · {v.aprovada ? "aprovada" : "rejeitada"}
                        </span>
                      )}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      {/* painel da votação selecionada */}
      <div>
        {!sel ? (
          <Vazio>escolha uma votação.</Vazio>
        ) : (
          <Card className="p-5 pt-6">
            <div className="flex items-start justify-between gap-3 pl-5">
              <p className="max-w-[46ch] font-editorial text-[1.02rem] leading-snug text-ink">
                {sel.descricao}
              </p>
              <Carimbo
                fonte="CÂMARA"
                cache={votos.dados?.meta?.cache as string | undefined}
                ms={votos.ms}
                erro={!!votos.erro}
              />
            </div>

            <div className="my-5 pl-5">
              {votos.erro ? (
                <ErroBox erro={votos.erro} aoTentar={votos.recarregar} />
              ) : votos.carregando && !votos.dados ? (
                <Esqueleto linhas={5} />
              ) : placar ? (
                <EmTransicao ativo={votos.carregando}>
                  <Placar placar={placar} />

                  <div className="mt-6 mb-3 flex flex-wrap items-center gap-2">
                    <FiltroChip ativo={filtro === null} aoClicar={() => setFiltro(null)}>
                      todos ({deputados.length})
                    </FiltroChip>
                    {ORDEM.filter((v) => placar[v]).map((v) => (
                      <FiltroChip key={v} ativo={filtro === v} aoClicar={() => setFiltro(v)}>
                        {v} ({placar[v]})
                      </FiltroChip>
                    ))}
                  </div>

                  <ul className="flex max-h-128 flex-col divide-y divide-line overflow-y-auto">
                    {filtrados.map((d) => (
                      <li
                        key={d.deputado_id}
                        className="flex items-center justify-between gap-3 py-1.5"
                      >
                        <span className="min-w-0">
                          <span className="block truncate text-sm text-ink">{d.deputado}</span>
                          <span className="num text-xs text-muted">
                            {[d.partido, d.uf].filter(Boolean).join(" · ")}
                          </span>
                        </span>
                        <span className={`num shrink-0 text-xs font-semibold ${corVoto(d.voto).txt}`}>
                          {d.voto}
                        </span>
                      </li>
                    ))}
                  </ul>
                </EmTransicao>
              ) : (
                <Vazio>{aviso ?? "esta votação não registra voto por deputado."}</Vazio>
              )}
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}

function PorDeputado() {
  const [texto, setTexto] = useState("");
  const [q, setQ] = useState("");
  const consulta = useBalcao<VotosDeputadoOut>(
    q ? caminho("votos", { deputado: q, votacoes: 25 }) : null,
  );
  const res = consulta.dados;

  return (
    <div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          setQ(texto.trim());
        }}
        className="mb-5 flex flex-wrap items-center gap-2"
      >
        <input
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          placeholder="nome do candidato (ex: Kim Kataguiri, Tabata)"
          className="w-80 rounded-md border border-line bg-surface px-3 py-1.5 text-ink placeholder:text-muted"
        />
        <button className="num rounded-md border border-accent bg-accent px-3 py-1.5 text-xs uppercase tracking-wider text-surface">
          ver votos
        </button>
      </form>

      {!q ? (
        <Vazio>digite o nome de um deputado para ver como ele votou.</Vazio>
      ) : consulta.erro ? (
        <ErroBox erro={consulta.erro} aoTentar={consulta.recarregar} />
      ) : consulta.carregando && !res ? (
        <div>
          <p className="kicker mb-3 pulsar">varrendo as votações recentes do plenário…</p>
          <Esqueleto linhas={6} />
        </div>
      ) : res ? (
        <EmTransicao ativo={consulta.carregando}>
          <div className="mb-4 flex items-end justify-between gap-3">
            <div>
              <h2 className="font-display text-2xl leading-tight text-ink">{res.deputado.nome}</h2>
              <p className="num text-xs text-muted">
                {[res.deputado.partido, res.deputado.uf].filter(Boolean).join(" · ")} · {res.total} de{" "}
                {res.votacoes_analisadas} votações com voto registrado
              </p>
            </div>
            <Carimbo
              fonte="CÂMARA"
              cache={undefined}
              ms={consulta.ms}
              erro={!!consulta.erro}
            />
          </div>

          {res.votos.length === 0 ? (
            <Vazio>
              nenhum voto nominal nas votações recentes — as votações do período foram simbólicas
              (aprovadas de viva voz, sem registro individual) ou o deputado não estava presente.
            </Vazio>
          ) : (
            <ul className="flex flex-col gap-2">
              {res.votos.map((v) => (
                <li key={v.votacao_id}>
                  <Card className="p-4 pl-7">
                    <div className="flex items-start justify-between gap-4">
                      <p className="font-editorial text-[1rem] leading-snug text-ink/90">
                        {v.descricao}
                      </p>
                      <span
                        className={`num shrink-0 rounded-sm border px-2 py-0.5 text-xs font-semibold uppercase tracking-wider ${corVoto(v.voto).txt} border-current/30`}
                      >
                        {v.voto}
                      </span>
                    </div>
                    <p className="num mt-1.5 text-xs text-muted">
                      {formataData(v.data)}
                      {v.aprovada != null && (
                        <span className={v.aprovada ? "text-ok" : "text-accent"}>
                          {" · "}
                          {v.aprovada ? "aprovada" : "rejeitada"}
                        </span>
                      )}
                    </p>
                  </Card>
                </li>
              ))}
            </ul>
          )}

          <p className="mt-5 font-editorial text-sm italic text-muted">
            Mostra as votações nominais mais recentes do plenário. O histórico completo do ano vive
            num arquivo de dados abertos da Câmara — está no nosso roteiro trazer ele inteiro.
          </p>
        </EmTransicao>
      ) : null}
    </div>
  );
}

function Placar({ placar }: { placar: Record<string, number> }) {
  const ordemDe = (v: string) => {
    const i = ORDEM.indexOf(v);
    return i === -1 ? ORDEM.length : i;
  };
  const itens = Object.entries(placar).sort((a, b) => ordemDe(a[0]) - ordemDe(b[0]));
  const total = itens.reduce((s, [, n]) => s + n, 0) || 1;
  return (
    <ul className="flex flex-col gap-2.5">
      {itens.map(([voto, n]) => (
        <li key={voto}>
          <div className="mb-1 flex items-baseline justify-between">
            <span className="text-sm text-ink/85">{voto}</span>
            <span className={`num text-sm ${corVoto(voto).txt}`}>{n}</span>
          </div>
          <div className="h-2.5 overflow-hidden rounded-sm bg-surface-2">
            <div
              className={`h-full rounded-sm ${corVoto(voto).bar}`}
              style={{ width: `${Math.max((n / total) * 100, 1.5)}%` }}
            />
          </div>
        </li>
      ))}
    </ul>
  );
}

function FiltroChip({
  ativo,
  aoClicar,
  children,
}: {
  ativo: boolean;
  aoClicar: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={aoClicar}
      aria-pressed={ativo}
      className={`num rounded-md border px-2.5 py-1 text-xs transition-colors ${
        ativo ? "border-accent/40 bg-accent/10 text-accent" : "border-line bg-surface text-muted hover:text-ink"
      }`}
    >
      {children}
    </button>
  );
}
