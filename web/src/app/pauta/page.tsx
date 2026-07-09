"use client";

import { useState } from "react";
import { CadernoHeader } from "@/components/Caderno";
import { Card } from "@/components/Card";
import { Carimbo } from "@/components/Carimbo";
import { SeloFonte } from "@/components/SeloFonte";
import { Esqueleto, ErroBox, Vazio, EmTransicao } from "@/components/Estados";
import { LerMais } from "@/components/LerMais";
import { useBalcao } from "@/hooks/useBalcao";
import { caminho, formataData } from "@/lib/api";
import type {
  NormalizedResponse,
  ProposicaoDetalhe,
  Votacao,
  VotacaoCompleta,
  VotoDeputado,
} from "@/lib/types";

const FONTE_CAMARA = {
  nome: "Câmara dos Deputados — Dados Abertos",
  url: "https://dadosabertos.camara.leg.br/",
  nota: "Votações e proposições em tramitação, direto da API oficial da Câmara — o que o plenário decidiu e o que está na fila.",
};

interface Proposicao {
  fonte: string;
  id: number;
  tipo: string;
  numero: number | null;
  ano: number | null;
  ementa: string;
}

interface EventoAndou {
  data: string | null;
  orgao: string | null;
  descricao: string | null;
  marco: string | null;
}

interface Novidade {
  fonte: string;
  id: number;
  titulo: string;
  ementa: string | null;
  andou: EventoAndou[];
}

type Aba = "andou" | "votacoes" | "proposicoes";

const ABAS: [Aba, string][] = [
  ["andou", "Andou"],
  ["votacoes", "Votações"],
  ["proposicoes", "Proposições"],
];

const PERIODOS = [
  { dias: 7, label: "7 dias" },
  { dias: 15, label: "15 dias" },
  { dias: 30, label: "30 dias" },
];

const TIPOS = ["", "PL", "PEC", "PLP", "MPV"];

function dataISO(diasAtras: number): string {
  const d = new Date();
  d.setDate(d.getDate() - diasAtras);
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const dia = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${m}-${dia}`;
}

// 'YYYY-MM-DD' -> 'dd/mm' pro selo mostrar a janela do dado
function curta(iso: string): string {
  const [, m, d] = iso.split("-");
  return `${d}/${m}`;
}

// a história por trás da votação: o parecer que foi votado e a(s)
// proposição(ões) afetada(s), com ementa — "Aprovado o Parecer" deixa de
// ser enigma
function MateriaDaVotacao({ id }: { id: string }) {
  const r = useBalcao<NormalizedResponse<VotacaoCompleta>>(caminho(`camara/votacoes/${id}`));
  const v = r.dados?.dados?.[0];

  if (r.erro) return <ErroBox erro={r.erro} aoTentar={r.recarregar} />;
  if (r.carregando && !v) return <Esqueleto linhas={2} />;
  if (!v || (!v.parecer && !v.proposicoes.length)) {
    return (
      <p className="font-editorial text-sm italic text-muted">
        a Câmara não detalhou a matéria desta votação.
      </p>
    );
  }
  return (
    <div className="flex flex-col gap-3">
      {v.parecer && (
        <div>
          <p className="kicker mb-1">o que foi votado</p>
          <LerMais
            texto={v.parecer}
            limite={260}
            className="font-editorial text-sm leading-relaxed text-ink/90"
          />
        </div>
      )}
      {v.proposicoes.map((p) => (
        <div key={p.id} className="rounded-md border border-line bg-surface p-3">
          <p className="num flex flex-wrap items-baseline gap-x-3 text-xs font-semibold uppercase tracking-wider text-accent">
            <span>{p.titulo}</span>
            <a
              href={`https://www.camara.leg.br/propostas-legislativas/${p.id}`}
              target="_blank"
              rel="noreferrer"
              className="rounded-md border border-accent/50 px-2.5 py-0.5 font-normal text-accent transition-colors hover:bg-accent hover:text-surface"
            >
              tramitação completa →
            </a>
          </p>
          {p.ementa && (
            <LerMais
              texto={p.ementa}
              limite={280}
              className="mt-1 font-editorial text-sm leading-relaxed text-ink/85"
            />
          )}
        </div>
      ))}
    </div>
  );
}

// o voto a voto de uma votação, aberto sob demanda — placar, quem foi a
// favor e quem foi contra (votação simbólica avisa que não tem)
function VotosDaVotacao({ id }: { id: string }) {
  const r = useBalcao<NormalizedResponse<VotoDeputado>>(caminho(`camara/votacoes/${id}/votos`));
  const votos = r.dados?.dados ?? [];
  const aviso = r.dados?.meta?.aviso as string | undefined;
  const placar = (r.dados?.meta?.placar as Record<string, number> | undefined) ?? {};
  const sim = votos.filter((v) => v.voto === "Sim");
  const nao = votos.filter((v) => v.voto === "Não");
  const outros = votos.length - sim.length - nao.length;

  if (r.erro) return <ErroBox erro={r.erro} aoTentar={r.recarregar} />;
  if (r.carregando && !r.dados) return <Esqueleto linhas={3} />;
  if (aviso || !votos.length) {
    return (
      <p className="font-editorial text-sm italic text-muted">
        {aviso ?? "sem voto individual registrado."}
      </p>
    );
  }
  return (
    <div>
      <div className="mb-3 flex flex-wrap gap-2">
        {Object.entries(placar).map(([voto, n]) => (
          <span
            key={voto}
            className={`num rounded-full border px-2.5 py-0.5 text-xs ${
              voto === "Sim"
                ? "border-ok/40 bg-ok/10 text-ok"
                : voto === "Não"
                  ? "border-erro/40 bg-erro/10 text-erro"
                  : "border-line bg-surface text-muted"
            }`}
          >
            {voto}: {n}
          </span>
        ))}
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <p className="kicker mb-1.5 text-ok">a favor ({sim.length})</p>
          <ul className="max-h-56 overflow-y-auto pr-1 text-sm leading-relaxed text-ink/85">
            {sim.map((v) => (
              <li key={v.deputado_id}>
                {v.deputado}
                <span className="num ml-1.5 text-xs text-muted">
                  {[v.partido, v.uf].filter(Boolean).join("·")}
                </span>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <p className="kicker mb-1.5 text-erro">contra ({nao.length})</p>
          <ul className="max-h-56 overflow-y-auto pr-1 text-sm leading-relaxed text-ink/85">
            {nao.map((v) => (
              <li key={v.deputado_id}>
                {v.deputado}
                <span className="num ml-1.5 text-xs text-muted">
                  {[v.partido, v.uf].filter(Boolean).join("·")}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>
      {outros > 0 && (
        <p className="num mt-2 text-xs text-muted">+ {outros} abstenções/obstruções/outros</p>
      )}
    </div>
  );
}

// classes do selo do marco, por sentido: verde aprovou, vermelho rejeitou/arquivou,
// petróleo virou norma (lei); o resto neutro
function corDoMarco(marco: string): string {
  const m = marco.toLowerCase();
  if (m.startsWith("aprovada")) return "border-ok/40 bg-ok/10 text-ok";
  if (m.startsWith("rejeitada") || m.includes("arquiv")) return "border-erro/40 bg-erro/10 text-erro";
  if (m.includes("norma")) return "border-accent-2/40 bg-accent-2/10 text-accent-2";
  return "border-line bg-surface text-muted";
}

// o feed que fecha o acompanhamento: só as proposições que DECIDIRAM algo no
// período (aprovada na CCJ, rejeitada, virou norma), já com o marco em português.
// Não é a lista de tudo que tramitou — é o que virou notícia.
function Andou({ dias }: { dias: number }) {
  const r = useBalcao<NormalizedResponse<Novidade>>(
    caminho("camara/proposicoes/andaram", { dias }),
  );
  const novidades = r.dados?.dados ?? [];
  const tramitaram = r.dados?.meta?.tramitaram as number | undefined;

  return (
    <div>
      <p className="kicker mb-3 flex items-center justify-between">
        <span>as decisões da semana</span>
        <Carimbo fonte="CÂMARA" cache={r.dados?.meta?.cache as string | undefined} ms={r.ms} erro={!!r.erro} />
      </p>
      {r.erro ? (
        <ErroBox erro={r.erro} aoTentar={r.recarregar} />
      ) : r.carregando && !r.dados ? (
        <Esqueleto linhas={6} />
      ) : novidades.length ? (
        <EmTransicao ativo={r.carregando}>
          {tramitaram ? (
            <p className="mb-3 font-editorial text-sm italic text-muted">
              De {tramitaram} proposições de peso (PEC, PLP, MPV) que se mexeram,{" "}
              {novidades.length === 1 ? "esta 1 teve" : `estas ${novidades.length} tiveram`} uma decisão de
              verdade.
            </p>
          ) : null}
          <Card className="divide-y divide-line p-0">
            {novidades.map((n) => {
              const topo = n.andou[0];
              return (
                <div key={n.id} className="px-5 py-3">
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
                    <span className="num text-xs font-semibold uppercase tracking-wider text-accent">
                      {n.titulo}
                    </span>
                    {topo?.marco && (
                      <span
                        className={`num rounded-full border px-2.5 py-0.5 text-[0.7rem] font-semibold ${corDoMarco(topo.marco)}`}
                      >
                        {topo.marco}
                      </span>
                    )}
                    {topo?.data && <span className="num text-xs text-muted">{formataData(topo.data)}</span>}
                    <a
                      href={`https://www.camara.leg.br/propostas-legislativas/${n.id}`}
                      target="_blank"
                      rel="noreferrer"
                      className="num text-xs text-accent transition-colors hover:text-accent-2"
                    >
                      na Câmara →
                    </a>
                  </div>
                  {n.ementa && (
                    <LerMais
                      texto={n.ementa}
                      limite={220}
                      className="mt-1 font-editorial text-sm leading-snug text-ink/90"
                    />
                  )}
                  {n.andou.length > 1 && (
                    <p className="num mt-1 text-xs text-muted">
                      + {n.andou.length - 1} {n.andou.length - 1 === 1 ? "outro marco" : "outros marcos"} no período
                    </p>
                  )}
                </div>
              );
            })}
          </Card>
        </EmTransicao>
      ) : (
        <Vazio>nenhuma decisão de peso (PEC/PLP/MPV) no período.</Vazio>
      )}
    </div>
  );
}

function Votacoes({ dias }: { dias: number }) {
  const r = useBalcao<NormalizedResponse<Votacao>>(
    caminho("camara/votacoes", { data_inicio: dataISO(dias), data_fim: dataISO(0), itens: 30 }),
  );
  const votacoes = r.dados?.dados ?? [];
  const [aberta, setAberta] = useState<string | null>(null);

  return (
    <div>
      <p className="kicker mb-3 flex items-center justify-between">
        <span>o plenário decidiu</span>
        <Carimbo fonte="CÂMARA" cache={r.dados?.meta?.cache as string | undefined} ms={r.ms} erro={!!r.erro} />
      </p>
      {r.erro ? (
        <ErroBox erro={r.erro} aoTentar={r.recarregar} />
      ) : r.carregando && !r.dados ? (
        <Esqueleto linhas={8} />
      ) : votacoes.length ? (
        <EmTransicao ativo={r.carregando}>
          <Card className="divide-y divide-line p-0">
            {votacoes.map((v) => (
              <div key={v.id} className="flex items-start gap-3 px-5 py-3">
                <span
                  className={`num mt-0.5 shrink-0 rounded-full px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wider ${
                    v.aprovada === true
                      ? "bg-ok/10 text-ok"
                      : v.aprovada === false
                        ? "bg-erro/10 text-erro"
                        : "bg-surface-2 text-muted"
                  }`}
                >
                  {v.aprovada === true ? "aprovada" : v.aprovada === false ? "rejeitada" : "registro"}
                </span>
                <div className="min-w-0 flex-1">
                  <LerMais
                    texto={v.descricao}
                    limite={200}
                    className="font-editorial text-sm leading-snug text-ink/90"
                  />
                  <p className="num mt-1 flex flex-wrap items-center gap-x-3 text-xs text-muted">
                    <span>
                      {formataData(v.data)}
                      {v.orgao && ` · ${v.orgao}`}
                    </span>
                    <button
                      onClick={() => setAberta(aberta === v.id ? null : v.id)}
                      aria-expanded={aberta === v.id}
                      className="uppercase tracking-wider text-accent transition-colors hover:text-accent-2"
                    >
                      {aberta === v.id ? "fechar ▴" : "ler mais: a matéria e os votos ▸"}
                    </button>
                  </p>
                  {aberta === v.id && (
                    <div className="mt-3 flex flex-col gap-4 border-t border-line pt-3">
                      <MateriaDaVotacao id={v.id} />
                      <div>
                        <p className="kicker mb-2">quem votou</p>
                        <VotosDaVotacao id={v.id} />
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </Card>
        </EmTransicao>
      ) : (
        <Vazio>nenhuma votação no período.</Vazio>
      )}
    </div>
  );
}

// o dossiê de um projeto: onde está, com quem, em que regime e o texto
// integral — aberto sob demanda
function DossieProposicao({ id }: { id: number }) {
  const r = useBalcao<NormalizedResponse<ProposicaoDetalhe>>(caminho(`camara/proposicoes/${id}`));
  const p = r.dados?.dados?.[0];

  if (r.erro) return <ErroBox erro={r.erro} aoTentar={r.recarregar} />;
  if (r.carregando && !p) return <Esqueleto linhas={2} />;
  if (!p) return null;
  return (
    <div className="flex flex-col gap-2">
      {p.ementa_detalhada && (
        <LerMais
          texto={p.ementa_detalhada}
          limite={300}
          className="font-editorial text-sm leading-relaxed text-ink/90"
        />
      )}
      <div className="flex flex-wrap gap-2">
        {p.situacao && (
          <span className="num rounded-full border border-accent-2/40 bg-accent-2/10 px-2.5 py-0.5 text-xs text-accent-2">
            {p.situacao}
          </span>
        )}
        {p.orgao && (
          <span className="num rounded-full border border-line bg-surface px-2.5 py-0.5 text-xs text-ink/80">
            está em: {p.orgao}
          </span>
        )}
        {p.regime && (
          <span className="num rounded-full border border-line bg-surface px-2.5 py-0.5 text-xs text-muted">
            {p.regime}
          </span>
        )}
      </div>
      {p.despacho && (
        <LerMais
          texto={`Despacho: ${p.despacho}`}
          limite={200}
          className="font-editorial text-xs leading-relaxed text-muted"
        />
      )}
      {p.keywords && (
        <p className="num text-xs text-muted">temas: {p.keywords.toLowerCase()}</p>
      )}
      {p.url_inteiro_teor && (
        <a
          href={p.url_inteiro_teor}
          target="_blank"
          rel="noreferrer"
          className="num w-fit rounded-md border border-accent px-3 py-1 text-xs uppercase tracking-wider text-accent transition-colors hover:bg-accent hover:text-surface"
        >
          ler o projeto na íntegra (PDF) →
        </a>
      )}
    </div>
  );
}

function Proposicoes({ dias }: { dias: number }) {
  const [tipo, setTipo] = useState("");
  const [busca, setBusca] = useState("");
  const [buscaAplicada, setBuscaAplicada] = useState("");
  const [abertaProp, setAbertaProp] = useState<number | null>(null);

  const r = useBalcao<NormalizedResponse<Proposicao>>(
    caminho("camara/proposicoes", {
      data_inicio: dataISO(dias),
      data_fim: dataISO(0),
      tipo: tipo || undefined,
      busca: buscaAplicada || undefined,
      itens: 30,
    }),
  );
  const proposicoes = r.dados?.dados ?? [];

  return (
    <div>
      <form
        className="mb-4 flex flex-wrap items-center gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          setBuscaAplicada(busca.trim());
        }}
      >
        <div className="inline-flex gap-0.5 rounded-md border border-line p-0.5">
          {TIPOS.map((t) => (
            <button
              key={t || "todos"}
              type="button"
              onClick={() => setTipo(t)}
              aria-pressed={tipo === t}
              className={`num rounded px-2.5 py-1 text-xs uppercase tracking-wider transition-colors ${
                tipo === t ? "bg-accent/15 font-semibold text-accent" : "text-muted hover:text-ink"
              }`}
            >
              {t || "todas"}
            </button>
          ))}
        </div>
        <input
          value={busca}
          onChange={(e) => setBusca(e.target.value)}
          placeholder="tema (ex: saúde, imposto)"
          className="rounded-md border border-line bg-surface px-2 py-1.5 text-sm text-ink focus:border-accent focus:outline-none"
        />
        <button
          type="submit"
          className="num rounded-md border border-ink/20 px-3 py-1.5 text-xs uppercase tracking-wider text-ink transition-colors hover:bg-surface-2"
        >
          buscar
        </button>
        <Carimbo fonte="CÂMARA" cache={r.dados?.meta?.cache as string | undefined} ms={r.ms} erro={!!r.erro} />
      </form>

      {r.erro ? (
        <ErroBox erro={r.erro} aoTentar={r.recarregar} />
      ) : r.carregando && !r.dados ? (
        <Esqueleto linhas={8} />
      ) : proposicoes.length ? (
        <EmTransicao ativo={r.carregando}>
          <Card className="divide-y divide-line p-0">
            {proposicoes.map((p) => (
              <div key={p.id} className="px-5 py-3">
                <p className="num flex flex-wrap items-baseline gap-x-3 text-xs font-semibold uppercase tracking-wider text-accent">
                  <span>
                    {p.tipo} {p.numero}/{p.ano}
                  </span>
                  <a
                    href={`https://www.camara.leg.br/propostas-legislativas/${p.id}`}
                    target="_blank"
                    rel="noreferrer"
                    className="rounded-md border border-accent/50 px-2.5 py-0.5 font-normal text-accent transition-colors hover:bg-accent hover:text-surface"
                  >
                    ver a tramitação na Câmara →
                  </a>
                  <button
                    onClick={() => setAbertaProp(abertaProp === p.id ? null : p.id)}
                    aria-expanded={abertaProp === p.id}
                    className="font-normal text-accent transition-colors hover:text-accent-2"
                  >
                    {abertaProp === p.id ? "fechar ▴" : "ler mais ▸"}
                  </button>
                </p>
                <LerMais
                  texto={p.ementa}
                  limite={260}
                  className="mt-1 font-editorial text-sm leading-snug text-ink/90"
                />
                {abertaProp === p.id && (
                  <div className="mt-3 border-t border-line pt-3">
                    <DossieProposicao id={p.id} />
                  </div>
                )}
              </div>
            ))}
          </Card>
        </EmTransicao>
      ) : (
        <Vazio>nada movimentado com esses filtros no período.</Vazio>
      )}
    </div>
  );
}

export default function CadernoPauta() {
  const [aba, setAba] = useState<Aba>("andou");
  const [dias, setDias] = useState(7);

  return (
    <div>
      <CadernoHeader
        numero="XVIII"
        kicker="Câmara dos Deputados"
        titulo="Em pauta"
        resumo="O Congresso desta semana: o que o plenário votou e quais projetos andaram. A mesma API oficial da Câmara dos cadernos de gastos e votos, recortada pelo período que interessa — o agora."
        referencia={`${curta(dataISO(dias))} a ${curta(dataISO(0))}`}
      />

      <div className="mb-6 flex flex-wrap items-center gap-4">
        <div className="inline-flex gap-0.5 rounded-md border border-line p-0.5">
          {ABAS.map(([v, label]) => (
            <button
              key={v}
              onClick={() => setAba(v)}
              aria-pressed={aba === v}
              className={`num rounded px-3 py-1 text-xs uppercase tracking-wider transition-colors ${
                aba === v ? "bg-accent/15 font-semibold text-accent" : "text-muted hover:text-ink"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          {PERIODOS.map((p) => (
            <button
              key={p.dias}
              onClick={() => setDias(p.dias)}
              aria-pressed={dias === p.dias}
              className={`num rounded-full border px-3 py-1 text-xs uppercase tracking-wider transition-colors ${
                dias === p.dias
                  ? "border-accent bg-accent text-surface"
                  : "border-line text-muted hover:border-accent hover:text-accent"
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {aba === "andou" ? (
        <Andou dias={dias} />
      ) : aba === "votacoes" ? (
        <Votacoes dias={dias} />
      ) : (
        <Proposicoes dias={dias} />
      )}

      <SeloFonte fonte={FONTE_CAMARA} />
    </div>
  );
}
