"use client";

/* eslint-disable @next/next/no-img-element */
import { useEffect, useState } from "react";
import { CadernoHeader } from "@/components/Caderno";
import { Card } from "@/components/Card";
import { Carimbo } from "@/components/Carimbo";
import { Kpi } from "@/components/Kpi";
import { BarrasGasto } from "@/components/BarrasGasto";
import { Seletor } from "@/components/Seletor";
import { SeloFonte } from "@/components/SeloFonte";
import { Termo } from "@/components/Termo";
import { Esqueleto, ErroBox, Vazio, EmTransicao } from "@/components/Estados";
import { useBalcao } from "@/hooks/useBalcao";
import { apiGet, caminho, formataBRL, formataData } from "@/lib/api";
import { ANO_ATUAL, anos } from "@/lib/datas";
import { UFS } from "@/lib/ufs";
import { PARTIDOS } from "@/lib/partidos";
import type {
  Deputado,
  Despesa,
  Discurso,
  GastosOut,
  NormalizedResponse,
  PerfilDeputado,
} from "@/lib/types";

const FONTE_CAMARA = {
  nome: "Câmara dos Deputados — Dados Abertos",
  url: "https://dadosabertos.camara.leg.br/",
  nota: "Deputados em exercício e a cota parlamentar (CEAP) de cada um, agregada por tipo de despesa — direto da API oficial da Câmara.",
};

// "todos" agrega o mandato inteiro (legislatura 57, que começou em 2023);
// as listas seguem o calendário sozinhas
type AnoSel = number | "todos";
const OPCOES_ANO: AnoSel[] = ["todos", ...anos(ANO_ATUAL, 2023)];
const ANOS_MANDATO = anos(2023, ANO_ATUAL);

export default function CadernoCamara() {
  const [uf, setUf] = useState("SP");
  const [partido, setPartido] = useState("");
  const [sel, setSel] = useState<Deputado | null>(null);
  const [ano, setAno] = useState<AnoSel>(ANO_ATUAL);

  const lista = useBalcao<NormalizedResponse<Deputado>>(
    caminho("camara/deputados", { uf, partido: partido || undefined, itens: 30 }),
  );
  const deputados = lista.dados?.dados ?? [];

  // mantém uma seleção válida conforme a lista muda
  useEffect(() => {
    if (!deputados.length) {
      setSel(null);
      return;
    }
    setSel((atual) => {
      if (atual && deputados.some((d) => d.id === atual.id)) return atual;
      return deputados[0];
    });
  }, [deputados]);

  return (
    <div>
      <CadernoHeader
        numero="II"
        kicker="Câmara dos Deputados"
        titulo="Quem são e quanto gastam"
        resumo="A lista de deputados em exercício e, para cada um, a cota parlamentar (CEAP) agregada por tipo de despesa. Filtre por estado ou partido e escolha um nome."
      />

      <div className="mb-6 flex flex-wrap items-center gap-3">
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
          value={partido}
          onChange={(e) => setPartido(e.target.value.toUpperCase())}
          placeholder="ou digite"
          className="w-24 rounded-md border border-line bg-surface px-2 py-1 text-sm uppercase text-ink placeholder:normal-case placeholder:text-muted"
        />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_1.1fr]">
        {/* lista de deputados */}
        <div>
          <p className="kicker mb-3">
            {lista.carregando && !lista.dados
              ? "consultando…"
              : `${deputados.length} deputados · ${uf}`}
          </p>
          {lista.erro ? (
            <ErroBox erro={lista.erro} aoTentar={lista.recarregar} />
          ) : lista.carregando && !lista.dados ? (
            <Esqueleto linhas={8} />
          ) : deputados.length === 0 ? (
            <Vazio>nenhum deputado para esse filtro.</Vazio>
          ) : (
            <EmTransicao ativo={lista.carregando}>
              <ul className="flex max-h-160 flex-col gap-1 overflow-y-auto pr-1">
                {deputados.map((d) => {
                  const ativo = sel?.id === d.id;
                  return (
                    <li key={d.id}>
                      <button
                        onClick={() => setSel(d)}
                        className={`flex w-full items-center gap-3 rounded-md border px-3 py-2 text-left transition-colors ${
                          ativo ? "border-accent/40 bg-surface" : "border-transparent hover:bg-surface/70"
                        }`}
                      >
                        <span className="h-10 w-8 shrink-0 overflow-hidden rounded-sm border border-line bg-surface-2">
                          {d.foto && (
                            <img src={d.foto} alt="" loading="lazy" className="h-full w-full object-cover" />
                          )}
                        </span>
                        <span className="min-w-0">
                          <span className="block truncate text-ink">{d.nome}</span>
                          <span className="num text-xs text-muted">
                            {[d.partido, d.uf].filter(Boolean).join(" · ")}
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

        {/* painel de gastos do selecionado */}
        <div>
          <div className="mb-3 flex items-center justify-between">
            <p className="kicker">
              <Termo t="ceap">Cota parlamentar</Termo>
            </p>
            <div className="flex gap-1">
              {OPCOES_ANO.map((a) => (
                <button
                  key={a}
                  onClick={() => setAno(a)}
                  aria-pressed={a === ano}
                  className={`num rounded px-1.5 py-0.5 text-xs transition-colors ${
                    a === ano ? "text-ink underline decoration-accent decoration-2 underline-offset-4" : "text-muted"
                  }`}
                >
                  {a === "todos" ? "Todos" : a}
                </button>
              ))}
            </div>
          </div>
          {!sel ? (
            <Vazio>escolha um deputado.</Vazio>
          ) : (
            <div className="flex flex-col gap-6">
              {ano === "todos" ? (
                <PainelTodosAnos deputado={sel} />
              ) : (
                <PainelGastos deputado={sel} ano={ano} />
              )}
              <PainelPerfil deputadoId={sel.id} />
              <PainelNotas deputadoId={sel.id} ano={ano} />
              <PainelDiscursos deputadoId={sel.id} />
            </div>
          )}
        </div>
      </div>

      <SeloFonte fonte={FONTE_CAMARA} />
    </div>
  );
}

function PainelGastos({ deputado, ano }: { deputado: Deputado; ano: number }) {
  const { dados, carregando, erro, ms, recarregar } = useBalcao<GastosOut>(
    caminho("gastos", { deputado: deputado.id, ano }),
  );

  return (
    <Card className="p-5 pt-6">
      <div className="flex items-start justify-between gap-3 pl-5">
        <div>
          <h2 className="font-display text-2xl leading-tight text-ink">{deputado.nome}</h2>
          <p className="num text-xs text-muted">
            {[deputado.partido, deputado.uf].filter(Boolean).join(" · ")} · {ano}
          </p>
        </div>
        <Carimbo fonte="CÂMARA" ms={ms} erro={!!erro} />
      </div>

      <div className="my-5 pl-5">
        {erro ? (
          <ErroBox erro={erro} aoTentar={recarregar} />
        ) : carregando && !dados ? (
          <Esqueleto linhas={5} />
        ) : dados ? (
          <EmTransicao ativo={carregando}>
            <div className="mb-5 flex flex-wrap gap-8">
              <Kpi rotulo="Total no ano" valor={Number(dados.valor_total)} formato="brl" tom="accent" />
              <Kpi rotulo="Documentos" valor={dados.total_documentos} />
            </div>
            {dados.total_documentos > 0 ? (
              <BarrasGasto porTipo={dados.por_tipo} />
            ) : (
              <Vazio>nenhuma despesa registrada em {ano}.</Vazio>
            )}
          </EmTransicao>
        ) : null}
      </div>
    </Card>
  );
}

// "todos os anos": busca cada ano do mandato em paralelo e mostra a barra por ano
function PainelTodosAnos({ deputado }: { deputado: Deputado }) {
  const [estado, setEstado] = useState<{
    carregando: boolean;
    anos: { ano: number; total: number; docs: number }[];
  }>({ carregando: true, anos: [] });

  useEffect(() => {
    let vivo = true;
    setEstado({ carregando: true, anos: [] });
    Promise.all(
      ANOS_MANDATO.map((a) =>
        apiGet<GastosOut>(caminho("gastos", { deputado: deputado.id, ano: a }))
          .then((r) => ({ ano: a, total: Number(r.valor_total), docs: r.total_documentos }))
          .catch(() => ({ ano: a, total: 0, docs: 0 })),
      ),
    ).then((res) => {
      if (vivo) setEstado({ carregando: false, anos: res });
    });
    return () => {
      vivo = false;
    };
  }, [deputado.id]);

  const max = Math.max(...estado.anos.map((a) => a.total), 1);
  const totalGeral = estado.anos.reduce((s, a) => s + a.total, 0);
  const docsGeral = estado.anos.reduce((s, a) => s + a.docs, 0);

  return (
    <Card className="p-5 pt-6">
      <div className="flex items-start justify-between gap-3 pl-5">
        <div>
          <h2 className="font-display text-2xl leading-tight text-ink">{deputado.nome}</h2>
          <p className="num text-xs text-muted">
            {[deputado.partido, deputado.uf].filter(Boolean).join(" · ")} · mandato 2023–2026
          </p>
        </div>
        <Carimbo fonte="CÂMARA" ms={null} />
      </div>

      <div className="my-5 pl-5">
        {estado.carregando ? (
          <Esqueleto linhas={4} />
        ) : (
          <>
            <div className="mb-5 flex flex-wrap gap-8">
              <Kpi rotulo="Total no mandato" valor={totalGeral} formato="brl" tom="accent" />
              <Kpi rotulo="Documentos" valor={docsGeral} />
            </div>
            <ul className="flex flex-col gap-2.5">
              {estado.anos.map((a) => (
                <li key={a.ano}>
                  <div className="mb-1 flex items-baseline justify-between">
                    <span className="num text-sm text-ink/85">{a.ano}</span>
                    <span className="num text-sm text-muted">{formataBRL(a.total)}</span>
                  </div>
                  <div className="h-2.5 overflow-hidden rounded-sm bg-surface-2">
                    <div
                      className="h-full rounded-sm bg-accent-2"
                      style={{ width: `${Math.max((a.total / max) * 100, 1.5)}%` }}
                    />
                  </div>
                </li>
              ))}
            </ul>
          </>
        )}
      </div>
    </Card>
  );
}

// tira o nome da rede a partir do domínio do link
function rotuloRede(url: string): string {
  try {
    const host = new URL(url).hostname.replace(/^www\./, "").toLowerCase();
    if (host.includes("twitter") || host === "x.com") return "Twitter/X";
    if (host.includes("instagram")) return "Instagram";
    if (host.includes("facebook")) return "Facebook";
    if (host.includes("youtube") || host.includes("youtu.be")) return "YouTube";
    if (host.includes("tiktok")) return "TikTok";
    return host;
  } catch {
    return url;
  }
}

// a ficha civil do deputado: formação, origem, mandato, gabinete e redes
function PainelPerfil({ deputadoId }: { deputadoId: number }) {
  const { dados, carregando, erro, recarregar } = useBalcao<NormalizedResponse<PerfilDeputado>>(
    caminho(`camara/deputados/${deputadoId}/perfil`),
  );
  const perfil = dados?.dados[0] ?? null;

  const linhas: [string, string][] = [];
  if (perfil) {
    if (perfil.escolaridade) linhas.push(["escolaridade", perfil.escolaridade]);
    if (perfil.naturalidade) linhas.push(["naturalidade", perfil.naturalidade]);
    if (perfil.nascimento) linhas.push(["nascimento", formataData(perfil.nascimento)]);
    const mandato = [perfil.situacao, perfil.condicao].filter(Boolean).join(" · ");
    if (mandato) linhas.push(["mandato", mandato]);
    const contato = [
      perfil.gabinete ? `gabinete ${perfil.gabinete}` : null,
      perfil.telefone_gabinete ? `tel ${perfil.telefone_gabinete}` : null,
    ]
      .filter(Boolean)
      .join(" · ");
    if (contato) linhas.push(["contato", contato]);
  }

  // carregou e não veio nada: a seção some em silêncio
  if (!carregando && !erro && !perfil) return null;

  return (
    <div>
      <p className="kicker mb-3">quem é</p>
      {erro ? (
        <ErroBox erro={erro} aoTentar={recarregar} />
      ) : carregando && !dados ? (
        <Esqueleto linhas={3} />
      ) : perfil ? (
        <EmTransicao ativo={carregando}>
          <Card className="p-4 pl-7">
            <ul className="flex flex-col gap-1.5">
              {linhas.map(([rotulo, valor]) => (
                <li key={rotulo} className="flex items-baseline gap-3">
                  <span className="num w-28 shrink-0 text-xs uppercase tracking-wider text-muted">
                    {rotulo}
                  </span>
                  <span className="min-w-0 text-sm text-ink/90">{valor}</span>
                </li>
              ))}
            </ul>
            {perfil.redes.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-2">
                {perfil.redes.map((url) => (
                  <a
                    key={url}
                    href={url}
                    target="_blank"
                    rel="noreferrer"
                    className="num rounded-md border border-line bg-surface-2/60 px-2 py-0.5 text-xs text-ink/80 transition-colors hover:border-accent/40 hover:text-accent"
                  >
                    {rotuloRede(url)} ↗
                  </a>
                ))}
              </div>
            )}
          </Card>
        </EmTransicao>
      ) : null}
    </div>
  );
}

// as notas fiscais mais recentes por trás do agregado do painel de cima
function PainelNotas({ deputadoId, ano }: { deputadoId: number; ano: AnoSel }) {
  const { dados, carregando, erro, recarregar } = useBalcao<NormalizedResponse<Despesa>>(
    caminho(`camara/deputados/${deputadoId}/despesas`, {
      ano: ano === "todos" ? undefined : ano,
      itens: 6,
    }),
  );
  const notas = dados?.dados ?? [];

  return (
    <div>
      <p className="kicker mb-3">
        <Termo t="ceap">as últimas notas</Termo>
      </p>
      {erro ? (
        <ErroBox erro={erro} aoTentar={recarregar} />
      ) : carregando && !dados ? (
        <Esqueleto linhas={4} />
      ) : notas.length === 0 ? (
        <Vazio>nenhuma nota nesse período.</Vazio>
      ) : (
        <EmTransicao ativo={carregando}>
          <Card className="p-4 pl-7">
            <ul className="flex flex-col divide-y divide-line">
              {notas.map((n, i) => (
                <li key={`${n.data}-${n.valor}-${i}`} className="flex items-start justify-between gap-3 py-2 first:pt-0 last:pb-0">
                  <span className="min-w-0">
                    <span className="block truncate text-sm text-ink">{n.tipo}</span>
                    <span className="num block truncate text-xs text-muted">
                      {n.fornecedor} · {formataData(n.data)}
                    </span>
                  </span>
                  <span className="shrink-0 text-right">
                    <span className="num block text-sm text-ink">{formataBRL(n.valor)}</span>
                    {n.valor_glosa && Number(n.valor_glosa) > 0 && (
                      <span className="num block text-xs text-erro">
                        glosa {formataBRL(n.valor_glosa)}
                      </span>
                    )}
                    {n.url_documento && (
                      <a
                        href={n.url_documento}
                        target="_blank"
                        rel="noreferrer"
                        className="num text-xs text-accent-2 transition-colors hover:text-accent"
                      >
                        ver a nota →
                      </a>
                    )}
                  </span>
                </li>
              ))}
            </ul>
          </Card>
        </EmTransicao>
      )}
    </div>
  );
}

// os últimos discursos em plenário, com a transcrição dobrada por padrão
function PainelDiscursos({ deputadoId }: { deputadoId: number }) {
  const { dados, carregando, erro, recarregar } = useBalcao<NormalizedResponse<Discurso>>(
    caminho(`camara/deputados/${deputadoId}/discursos`, { itens: 3 }),
  );
  const discursos = dados?.dados ?? [];

  return (
    <div>
      <p className="kicker mb-3">na tribuna</p>
      {erro ? (
        <ErroBox erro={erro} aoTentar={recarregar} />
      ) : carregando && !dados ? (
        <Esqueleto linhas={3} />
      ) : discursos.length === 0 ? (
        <Vazio>sem discursos recentes.</Vazio>
      ) : (
        <EmTransicao ativo={carregando}>
          <Card className="p-4 pl-7">
            <ul className="flex flex-col divide-y divide-line">
              {discursos.map((d, i) => (
                <DiscursoItem key={`${d.data}-${i}`} discurso={d} />
              ))}
            </ul>
          </Card>
        </EmTransicao>
      )}
    </div>
  );
}

function DiscursoItem({ discurso: d }: { discurso: Discurso }) {
  const [aberto, setAberto] = useState(false);
  return (
    <li className="py-2.5 first:pt-0 last:pb-0">
      <p className="num text-xs text-muted">
        {formataData(d.data)}
        {d.tipo ? ` · ${d.tipo}` : ""}
      </p>
      {d.sumario && (
        <p className="mt-1 font-editorial text-[0.95rem] leading-snug text-ink/90">{d.sumario}</p>
      )}
      <div className="mt-1.5 flex flex-wrap items-center gap-3">
        {d.transcricao && (
          <button
            onClick={() => setAberto((a) => !a)}
            aria-expanded={aberto}
            className="num text-xs uppercase tracking-wider text-accent-2 transition-colors hover:text-accent"
          >
            {aberto ? "fechar a transcrição" : "ler a transcrição"}
          </button>
        )}
        {d.url_video && (
          <a
            href={d.url_video}
            target="_blank"
            rel="noreferrer"
            className="num text-xs text-muted transition-colors hover:text-ink"
          >
            ▶ vídeo
          </a>
        )}
      </div>
      {d.transcricao && (
        <div
          className={`grid transition-[grid-template-rows] duration-300 ${
            aberto ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
          }`}
        >
          <div className="overflow-hidden">
            <p className="mt-2 whitespace-pre-line border-l-2 border-line pl-3 font-editorial text-sm leading-relaxed text-ink/80">
              {d.transcricao}
            </p>
          </div>
        </div>
      )}
    </li>
  );
}
