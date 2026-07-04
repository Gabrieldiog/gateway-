"use client";

import { useEffect, useState } from "react";
import { CadernoHeader } from "@/components/Caderno";
import { Card } from "@/components/Card";
import { Carimbo } from "@/components/Carimbo";
import { SeloFonte } from "@/components/SeloFonte";
import { Esqueleto, ErroBox, Vazio, EmTransicao } from "@/components/Estados";
import { useBalcao } from "@/hooks/useBalcao";
import { caminho, formataData } from "@/lib/api";
import type { DatasetCKAN, NormalizedResponse } from "@/lib/types";

const FONTE_CKAN = {
  nome: "dados.gov.br e portais CKAN dos órgãos (ANEEL, ANTT, MME)",
  url: "https://dados.gov.br/",
  nota: "Catálogos oficiais de dados abertos, consultados direto na API CKAN de cada órgão.",
};

const PORTAIS = [
  { id: "aneel", nome: "ANEEL", sub: "energia elétrica" },
  { id: "mme", nome: "MME", sub: "minas e energia" },
  { id: "antt", nome: "ANTT", sub: "transporte terrestre" },
];

export default function CadernoDados() {
  const [portal, setPortal] = useState("aneel");
  const [texto, setTexto] = useState("");
  const [q, setQ] = useState("");
  const [ds, setDs] = useState<DatasetCKAN | null>(null);
  const [recurso, setRecurso] = useState<string | null>(null);

  // troca de portal ou nova busca zera a seleção
  useEffect(() => {
    setDs(null);
    setRecurso(null);
  }, [portal, q]);

  const lista = useBalcao<NormalizedResponse<DatasetCKAN>>(
    caminho(`${portal}/datasets`, { q: q || undefined, limite: 15 }),
  );
  const datasets = lista.dados?.dados ?? [];

  return (
    <div>
      <CadernoHeader
        numero="XI"
        kicker="Dados Abertos · CKAN"
        titulo="Os portais de dados abertos"
        resumo="ANEEL, MME e ANTT publicam em CKAN — o mesmo padrão atrás de um motor só no Balcão. Escolha o portal, busque um conjunto e abra as linhas reais (datastore)."
        referencia={ds?.atualizado ? `atualizado em ${formataData(ds.atualizado.slice(0, 10))}` : undefined}
      />

      <div className="mb-5 flex flex-wrap items-center gap-2">
        {PORTAIS.map((p) => (
          <button
            key={p.id}
            onClick={() => setPortal(p.id)}
            aria-pressed={p.id === portal}
            className={`rounded-md border px-3 py-1.5 text-left transition-colors ${
              p.id === portal ? "border-accent/40 bg-surface" : "border-line hover:bg-surface/70"
            }`}
          >
            <span className="block text-sm text-ink">{p.nome}</span>
            <span className="num text-[0.68rem] text-muted">{p.sub}</span>
          </button>
        ))}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            setQ(texto.trim());
          }}
          className="flex items-center gap-2"
        >
          <input
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            placeholder="buscar conjunto…"
            className="w-full min-w-0 sm:w-52 rounded-md border border-line bg-surface px-3 py-1.5 text-ink placeholder:text-muted"
          />
          <button className="num rounded-md border border-line px-3 py-1.5 text-xs uppercase tracking-wider text-ink hover:bg-surface-2">
            buscar
          </button>
        </form>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_1.4fr]">
        <div>
          <div className="mb-3 flex items-center justify-between">
            <p className="kicker">
              {lista.carregando && !lista.dados ? "consultando…" : `${datasets.length} conjuntos`}
            </p>
            <Carimbo
              fonte={portal.toUpperCase()}
              cache={lista.dados?.meta?.cache as string | undefined}
              ms={lista.ms}
              erro={!!lista.erro}
            />
          </div>
          {lista.erro ? (
            <ErroBox erro={lista.erro} aoTentar={lista.recarregar} />
          ) : lista.carregando && !lista.dados ? (
            <Esqueleto linhas={8} />
          ) : datasets.length === 0 ? (
            <Vazio>nenhum conjunto.</Vazio>
          ) : (
            <EmTransicao ativo={lista.carregando}>
            <ul className="flex max-h-160 flex-col gap-1 overflow-y-auto pr-1">
              {datasets.map((d) => {
                const comDado = d.recursos.filter((r) => r.datastore);
                const ativo = ds?.id === d.id;
                return (
                  <li key={d.id}>
                    <button
                      onClick={() => {
                        setDs(d);
                        setRecurso(comDado[0]?.id ?? null);
                      }}
                      className={`flex w-full flex-col gap-0.5 rounded-md border px-3 py-2 text-left transition-colors ${
                        ativo ? "border-accent/40 bg-surface" : "border-transparent hover:bg-surface/70"
                      }`}
                    >
                      <span className="line-clamp-2 text-sm text-ink/90">{d.titulo}</span>
                      <span className="num text-xs text-muted">{comDado.length} recurso(s) com dados</span>
                    </button>
                  </li>
                );
              })}
            </ul>
            </EmTransicao>
          )}
        </div>

        <div>
          {!ds ? (
            <Vazio>escolha um conjunto pra ver as linhas.</Vazio>
          ) : (
            <TabelaRecurso portal={portal} dataset={ds} recurso={recurso} setRecurso={setRecurso} />
          )}
        </div>
      </div>

      <SeloFonte fonte={FONTE_CKAN} />
    </div>
  );
}

function TabelaRecurso({
  portal,
  dataset,
  recurso,
  setRecurso,
}: {
  portal: string;
  dataset: DatasetCKAN;
  recurso: string | null;
  setRecurso: (id: string) => void;
}) {
  const comDado = dataset.recursos.filter((r) => r.datastore);
  const linhas = useBalcao<NormalizedResponse<Record<string, unknown>>>(
    recurso ? caminho(`${portal}/dados/${recurso}`, { limite: 12 }) : null,
  );
  const campos = (linhas.dados?.meta?.campos as string[] | undefined) ?? [];
  const rows = linhas.dados?.dados ?? [];
  const total = linhas.dados?.meta?.total as number | undefined;

  return (
    <Card className="p-5 pl-7">
      <h2 className="font-display text-xl leading-tight text-ink">{dataset.titulo}</h2>
      <div className="my-3 flex flex-wrap gap-1.5">
        {comDado.map((r) => (
          <button
            key={r.id}
            onClick={() => setRecurso(r.id)}
            aria-pressed={r.id === recurso}
            className={`num rounded-md border px-2 py-1 text-[0.7rem] transition-colors ${
              r.id === recurso ? "border-accent/40 bg-accent/10 text-accent" : "border-line text-muted hover:text-ink"
            }`}
          >
            {r.nome || r.formato || "recurso"}
          </button>
        ))}
      </div>

      {!recurso ? (
        <Vazio>esse conjunto não tem recurso com datastore (só arquivo pra download).</Vazio>
      ) : linhas.erro ? (
        <ErroBox erro={linhas.erro} aoTentar={linhas.recarregar} />
      ) : linhas.carregando && !linhas.dados ? (
        <Esqueleto linhas={6} />
      ) : rows.length === 0 ? (
        <Vazio>recurso sem linhas.</Vazio>
      ) : (
        <EmTransicao ativo={linhas.carregando}>
        <div className="max-h-[75vh] overflow-auto">
          <table className="w-full text-left text-xs">
            <thead className="grudento">
              <tr className="border-b border-line">
                {campos.slice(0, 8).map((c) => (
                  <th key={c} className="num whitespace-nowrap py-1.5 pr-4 font-semibold text-muted">
                    {c}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                <tr key={i} className="border-b border-line/60">
                  {campos.slice(0, 8).map((c) => (
                    <td key={c} className="whitespace-nowrap py-1.5 pr-4 text-ink/85">
                      {String(row[c] ?? "—").slice(0, 38)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          <p className="num mt-3 text-xs text-muted">
            {total != null && `${total.toLocaleString("pt-BR")} linhas no total`}
            {campos.length > 8 && ` · mostrando 8 de ${campos.length} colunas`}
          </p>
        </div>
        </EmTransicao>
      )}
    </Card>
  );
}
