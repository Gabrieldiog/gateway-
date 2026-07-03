"use client";

/* eslint-disable @next/next/no-img-element */
import { useEffect, useState } from "react";
import { CadernoHeader } from "@/components/Caderno";
import { Card } from "@/components/Card";
import { Carimbo } from "@/components/Carimbo";
import { Seletor } from "@/components/Seletor";
import { SeloFonte } from "@/components/SeloFonte";
import { Esqueleto, ErroBox, Vazio, EmTransicao } from "@/components/Estados";
import { useBalcao } from "@/hooks/useBalcao";
import { caminho, formataData } from "@/lib/api";
import { UFS } from "@/lib/ufs";
import { PARTIDOS } from "@/lib/partidos";
import type {
  Deputado,
  NormalizedResponse,
  OrientacaoBancada,
  Votacao,
  VotoDeputado,
  VotosParlamentarOut,
} from "@/lib/types";

const FONTE_CAMARA = {
  nome: "Câmara dos Deputados — Dados Abertos",
  url: "https://dadosabertos.camara.leg.br/",
  nota: "Cada voto nominal de cada deputado, direto da API oficial da Câmara.",
};

const FONTE_SENADO = {
  nome: "Senado Federal — Dados Abertos Legislativos",
  url: "https://legis.senado.leg.br/dadosabertos/",
  nota: "As votações nominais do plenário do Senado, direto da API oficial.",
};

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

type Modo = "votacao" | "parlamentar";

export default function CadernoVotos() {
  const [modo, setModo] = useState<Modo>("votacao");

  return (
    <div>
      <CadernoHeader
        numero="VIII"
        kicker="Congresso Nacional"
        titulo="Como cada um votou"
        resumo="Duas lentes sobre o plenário: por votação, o voto de todos num projeto; por parlamentar, como o seu candidato — deputado ou senador — votou. Votações simbólicas (de viva voz) não registram voto individual."
      />

      <div className="mb-6 flex w-fit gap-1 rounded-md border border-line bg-surface p-1">
        {(["votacao", "parlamentar"] as Modo[]).map((m) => (
          <button
            key={m}
            onClick={() => setModo(m)}
            aria-pressed={m === modo}
            className={`num rounded px-3 py-1.5 text-xs uppercase tracking-wider transition-colors ${
              m === modo ? "bg-accent text-surface" : "text-muted hover:text-ink"
            }`}
          >
            {m === "votacao" ? "por votação" : "por parlamentar"}
          </button>
        ))}
      </div>

      {modo === "votacao" ? <PorVotacao /> : <PorParlamentar />}
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

  const orientacoes = useBalcao<NormalizedResponse<OrientacaoBancada>>(
    sel ? caminho(`camara/votacoes/${sel.id}/orientacoes`) : null,
  );
  const bancadas = orientacoes.dados?.dados ?? [];
  const avisoBancadas = orientacoes.dados?.meta?.aviso as string | undefined;

  // mapa partido -> orientação (só Sim/Não; Liberado não conta como ordem).
  // bancada pode vir como bloco ("PT-PCdoB-PV"), então cada pedaço vira chave.
  const ordemDoPartido = new Map<string, string>();
  for (const b of bancadas) {
    if (b.orientacao !== "Sim" && b.orientacao !== "Não") continue;
    for (const parte of b.bancada.split(/[\s\-/·,]+/)) {
      if (parte) ordemDoPartido.set(parte.toLowerCase(), b.orientacao);
    }
  }
  const contrariou = (d: VotoDeputado) => {
    if (d.voto !== "Sim" && d.voto !== "Não") return false;
    const ordem = d.partido ? ordemDoPartido.get(d.partido.toLowerCase()) : undefined;
    return ordem !== undefined && ordem !== d.voto;
  };
  const rebeldes = deputados.filter(contrariou).length;

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
        <p className="kicker mb-3">Câmara · Plenário · votações recentes</p>
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

                  {(bancadas.length > 0 || avisoBancadas) && (
                    <div className="mt-6">
                      <p className="kicker mb-2">como as bancadas orientaram</p>
                      {avisoBancadas ? (
                        <p className="font-editorial text-sm italic text-muted">{avisoBancadas}</p>
                      ) : (
                        <div className="flex flex-wrap gap-1.5">
                          {bancadas.map((b) => (
                            <ChipOrientacao key={`${b.bancada}-${b.orientacao}`} o={b} />
                          ))}
                        </div>
                      )}
                    </div>
                  )}

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

                  {rebeldes > 0 && (
                    <p className="num mb-2 text-xs text-accent">
                      {rebeldes === 1
                        ? "1 deputado votou contra a orientação do próprio partido"
                        : `${rebeldes} deputados votaram contra a orientação do próprio partido`}
                    </p>
                  )}

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
                            {contrariou(d) && (
                              <span className="num ml-2 rounded bg-accent/10 px-1.5 py-0.5 text-[0.6rem] uppercase tracking-wider text-accent">
                                contra o partido
                              </span>
                            )}
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

type Casa = "camara" | "senado";

function PorParlamentar() {
  const [casa, setCasa] = useState<Casa>("camara");
  const [uf, setUf] = useState("GO"); // predefinido pra já mostrar gente sem digitar
  const [partido, setPartido] = useState("");
  const [texto, setTexto] = useState("");
  const [sel, setSel] = useState<Deputado | null>(null);
  const [periodo, setPeriodo] = useState("recente"); // "recente" (scan) ou um ano (arquivo)

  const recurso = casa === "camara" ? "camara/deputados" : "senado/senadores";
  const lista = useBalcao<NormalizedResponse<Deputado>>(
    caminho(recurso, { uf, partido: partido || undefined, itens: casa === "camara" ? 60 : undefined }),
  );
  const todos = lista.dados?.dados ?? [];
  const parlamentares = texto
    ? todos.filter((p) => p.nome.toLowerCase().includes(texto.toLowerCase()))
    : todos;
  const cargo = casa === "camara" ? "deputado" : "senador";
  const cargoP = casa === "camara" ? "deputados" : "senadores";

  // mantém uma seleção válida conforme a lista muda
  useEffect(() => {
    if (!parlamentares.length) {
      setSel(null);
      return;
    }
    setSel((atual) => (atual && parlamentares.some((p) => p.id === atual.id) ? atual : parlamentares[0]));
  }, [parlamentares]);

  const anoSel = casa === "camara" && periodo !== "recente" ? Number(periodo) : undefined;
  const votos = useBalcao<VotosParlamentarOut>(
    sel
      ? caminho("votos", {
          parlamentar: sel.id,
          casa,
          votacoes: casa === "camara" && !anoSel ? 25 : undefined,
          ano: anoSel,
        })
      : null,
  );
  const res = votos.dados;

  return (
    <div>
      <div className="mb-5 flex flex-wrap items-center gap-3">
        <div className="flex gap-1 rounded-md border border-line bg-surface-2/60 p-1">
          {(["camara", "senado"] as Casa[]).map((c) => (
            <button
              key={c}
              onClick={() => setCasa(c)}
              aria-pressed={c === casa}
              className={`num rounded px-3 py-1 text-[0.7rem] uppercase tracking-wider transition-colors ${
                c === casa ? "bg-accent-2 text-surface" : "text-muted hover:text-ink"
              }`}
            >
              {c === "camara" ? "deputados" : "senadores"}
            </button>
          ))}
        </div>
        <label className="num flex items-center gap-2 text-xs uppercase tracking-wider text-muted">
          UF
          <Seletor value={uf} onChange={(e) => setUf(e.target.value)}>
            {UFS.map((u) => (
              <option key={u} value={u}>
                {u}
              </option>
            ))}
          </Seletor>
        </label>
        <label className="num flex items-center gap-2 text-xs uppercase tracking-wider text-muted">
          Partido
          <Seletor
            value={PARTIDOS.includes(partido) ? partido : ""}
            onChange={(e) => setPartido(e.target.value)}
          >
            <option value="">todos</option>
            {PARTIDOS.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </Seletor>
        </label>
        <input
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          placeholder="filtrar por nome"
          className="w-44 rounded-md border border-line bg-surface px-3 py-1.5 text-sm text-ink placeholder:text-muted"
        />
        {casa === "camara" && (
          <div className="flex items-center gap-1">
            <span className="num text-xs uppercase tracking-wider text-muted">período</span>
            {["recente", "2026", "2025", "2024", "2023"].map((p) => (
              <button
                key={p}
                onClick={() => setPeriodo(p)}
                aria-pressed={p === periodo}
                className={`num rounded px-1.5 py-0.5 text-xs transition-colors ${
                  p === periodo
                    ? "text-ink underline decoration-accent decoration-2 underline-offset-4"
                    : "text-muted"
                }`}
              >
                {p}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_1.4fr]">
        {/* lista de parlamentares da UF */}
        <div>
          <p className="kicker mb-3">
            {lista.carregando && !lista.dados ? "consultando…" : `${parlamentares.length} ${cargoP} · ${uf}`}
          </p>
          {lista.erro ? (
            <ErroBox erro={lista.erro} aoTentar={lista.recarregar} />
          ) : lista.carregando && !lista.dados ? (
            <Esqueleto linhas={6} />
          ) : parlamentares.length === 0 ? (
            <Vazio>nenhum {cargo} nesse filtro.</Vazio>
          ) : (
            <EmTransicao ativo={lista.carregando}>
              <ul className="flex max-h-160 flex-col gap-1 overflow-y-auto pr-1">
                {parlamentares.map((p) => {
                  const ativo = sel?.id === p.id;
                  return (
                    <li key={p.id}>
                      <button
                        onClick={() => setSel(p)}
                        className={`flex w-full items-center gap-3 rounded-md border px-3 py-2 text-left transition-colors ${
                          ativo ? "border-accent/40 bg-surface" : "border-transparent hover:bg-surface/70"
                        }`}
                      >
                        <span className="h-10 w-8 shrink-0 overflow-hidden rounded-sm border border-line bg-surface-2">
                          {p.foto && (
                            <img src={p.foto} alt="" loading="lazy" className="h-full w-full object-cover" />
                          )}
                        </span>
                        <span className="min-w-0">
                          <span className="block truncate text-ink">{p.nome}</span>
                          <span className="num text-xs text-muted">
                            {[p.partido, p.uf].filter(Boolean).join(" · ")}
                          </span>
                        </span>
                        {ativo && <span className="ml-auto h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />}
                      </button>
                    </li>
                  );
                })}
              </ul>
            </EmTransicao>
          )}
        </div>

        {/* votos do parlamentar selecionado */}
        <div>
          {!sel ? (
            <Vazio>escolha um {cargo}.</Vazio>
          ) : votos.erro ? (
            <ErroBox erro={votos.erro} aoTentar={votos.recarregar} />
          ) : votos.carregando && !res ? (
            <div>
              <p className="kicker mb-3">
                {casa === "senado"
                  ? "buscando o histórico do senador…"
                  : anoSel
                    ? `montando o histórico de ${anoSel}… (alguns segundos na 1ª vez)`
                    : "varrendo as votações recentes do plenário…"}
              </p>
              <Esqueleto linhas={6} />
            </div>
          ) : res ? (
            <EmTransicao ativo={votos.carregando}>
              <div className="mb-4 flex items-end justify-between gap-3">
                <div>
                  <h2 className="font-display text-2xl leading-tight text-ink">{res.parlamentar.nome}</h2>
                  <p className="num text-xs text-muted">
                    {[res.parlamentar.partido, res.parlamentar.uf].filter(Boolean).join(" · ")} ·{" "}
                    {res.casa === "senado"
                      ? `${res.total} votos no mandato`
                      : anoSel
                        ? `${res.total} votos em ${anoSel}`
                        : `${res.total} de ${res.analisadas} votações com voto`}
                  </p>
                </div>
                <Carimbo
                  fonte={res.casa === "senado" ? "SENADO" : "CÂMARA"}
                  cache={undefined}
                  ms={votos.ms}
                  erro={!!votos.erro}
                />
              </div>

              {res.votos.length === 0 ? (
                <Vazio>
                  nenhum voto nominal recente — as votações do período foram simbólicas (de viva voz,
                  sem registro individual) ou o parlamentar não estava presente.
                </Vazio>
              ) : (
                <ul className="flex max-h-160 flex-col gap-2 overflow-y-auto pr-1">
                  {res.votos.slice(0, 80).map((v) => (
                    <li key={v.votacao_id}>
                      <Card className="p-4 pl-7">
                        <div className="flex items-start justify-between gap-4">
                          <div className="min-w-0">
                            {v.materia && (
                              <span className="num mb-0.5 block text-xs text-accent-2">{v.materia}</span>
                            )}
                            <p className="font-editorial text-[1rem] leading-snug text-ink/90">
                              {v.descricao}
                            </p>
                          </div>
                          <span
                            className={`num shrink-0 rounded-sm border border-current/30 px-2 py-0.5 text-xs font-semibold uppercase tracking-wider ${corVoto(v.voto).txt}`}
                          >
                            {v.voto}
                          </span>
                        </div>
                        <p className="num mt-1.5 text-xs text-muted">
                          {formataData(v.data)}
                          {v.secreta && <span className="text-ocre"> · secreta</span>}
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
                {res.casa === "senado"
                  ? "Histórico completo do mandato, direto da API do Senado."
                  : anoSel
                    ? `Histórico completo de ${anoSel}, do arquivo anual de dados abertos da Câmara.`
                    : "Mostra as votações nominais mais recentes do plenário. Escolha um ano no período acima para o histórico completo."}
                {res.votos.length > 80 && ` Exibindo 80 de ${res.votos.length}.`}
              </p>
            </EmTransicao>
          ) : null}
        </div>
      </div>

      <SeloFonte fonte={casa === "camara" ? FONTE_CAMARA : FONTE_SENADO} />
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

// verde quando a bancada mandou Sim, rosa no Não, cinza quando liberou.
// Governo e Oposição ganham borda mais forte: são as orientações-farol.
function ChipOrientacao({ o }: { o: OrientacaoBancada }) {
  const farol = ["governo", "oposição", "oposicao"].includes(o.bancada.toLowerCase());
  const cor =
    o.orientacao === "Sim"
      ? farol
        ? "border-ok bg-ok/10 text-ok"
        : "border-ok/30 bg-ok/10 text-ok"
      : o.orientacao === "Não"
        ? farol
          ? "border-accent bg-accent/10 text-accent"
          : "border-accent/30 bg-accent/10 text-accent"
        : farol
          ? "border-muted bg-surface-2 text-muted"
          : "border-line bg-surface-2 text-muted";
  return (
    <span
      className={`num rounded-md border px-2 py-0.5 text-xs ${cor} ${farol ? "font-semibold" : ""}`}
    >
      {o.bancada} → {o.orientacao}
    </span>
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
