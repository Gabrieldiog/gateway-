"use client";

import { useState } from "react";
import { CadernoHeader } from "@/components/Caderno";
import { Card } from "@/components/Card";
import { Carimbo } from "@/components/Carimbo";
import { SeloFonte } from "@/components/SeloFonte";
import { Seletor } from "@/components/Seletor";
import { Esqueleto, ErroBox, Vazio, EmTransicao } from "@/components/Estados";
import { useBalcao } from "@/hooks/useBalcao";
import { caminho, formataData } from "@/lib/api";
import { CAPITAIS, UFS } from "@/lib/ufs";
import type { DiarioOficial, FonteDado, Municipio, NormalizedResponse } from "@/lib/types";

// as buscas que rendem história, um toque e a pauta abre
const SUGESTOES = [
  "“dispensa de licitação”",
  "nomeação",
  "exoneração",
  "emergência",
  "contratação",
];

export default function CadernoDiarios() {
  const [uf, setUf] = useState("GO");
  const [ibge, setIbge] = useState(CAPITAIS.GO);
  const [termo, setTermo] = useState("");
  const [busca, setBusca] = useState("");
  const [pagina, setPagina] = useState(1);

  const cidades = useBalcao<NormalizedResponse<Municipio>>(caminho("ibge/municipios", { uf }));
  const r = useBalcao<NormalizedResponse<DiarioOficial>>(
    busca ? caminho("diarios/busca", { municipio: ibge, q: busca, pagina }) : null,
  );
  const diarios = r.dados?.dados ?? [];
  const total = r.dados?.meta?.total_diarios as number | undefined;
  const temProxima = Boolean(r.dados?.meta?.tem_proxima);
  const aviso = r.dados?.meta?.aviso as string | undefined;
  const fonte = r.dados?.meta?.fonte as FonteDado | undefined;

  function dispara(q: string) {
    const limpo = q.trim();
    if (!limpo) return;
    setTermo(limpo);
    setBusca(limpo);
    setPagina(1);
  }

  return (
    <div>
      <CadernoHeader
        numero="XXIX"
        kicker="Querido Diário · Open Knowledge Brasil"
        titulo="Diários Oficiais"
        resumo="O papel oficial da sua prefeitura, aberto pra busca: digite um termo (o nome de uma empresa, “dispensa de licitação”, uma nomeação) e leia os trechos exatos onde ele aparece, dia a dia. Aspas buscam a frase exata."
      />

      <form
        className="mb-3 flex flex-wrap items-center gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          dispara(termo);
        }}
      >
        <Seletor
          value={uf}
          onChange={(e) => {
            setUf(e.target.value);
            setIbge(CAPITAIS[e.target.value]);
          }}
          aria-label="estado"
        >
          {UFS.map((u) => (
            <option key={u}>{u}</option>
          ))}
        </Seletor>
        <Seletor
          value={ibge}
          onChange={(e) => setIbge(e.target.value)}
          className="max-w-56"
          aria-label="cidade"
        >
          {(cidades.dados?.dados ?? []).map((m) => (
            <option key={m.id} value={String(m.id)}>
              {m.nome}
            </option>
          ))}
        </Seletor>
        <input
          value={termo}
          onChange={(e) => setTermo(e.target.value)}
          placeholder="o que procurar no diário?"
          className="w-full min-w-0 sm:w-64 rounded-md border border-line bg-surface px-3 py-2 text-sm text-ink focus:border-accent focus:outline-none"
        />
        <button
          type="submit"
          disabled={!termo.trim()}
          className="num rounded-md border border-accent bg-accent px-4 py-2 text-xs uppercase tracking-wider text-surface transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
        >
          buscar
        </button>
        {busca && <Carimbo fonte="OKBR" ms={r.ms} erro={!!r.erro} />}
      </form>

      <div className="mb-6 flex flex-wrap items-center gap-2">
        <span className="kicker">pautas prontas:</span>
        {SUGESTOES.map((s) => (
          <button
            key={s}
            onClick={() => dispara(s)}
            className="num rounded-full border border-line px-3 py-1 text-xs tracking-wider text-muted transition-colors hover:border-accent hover:text-accent"
          >
            {s}
          </button>
        ))}
      </div>

      {!busca ? (
        <Vazio>
          escolha a cidade, digite um termo e leia o diário oficial dela; a cobertura passa de
          400 municípios e cresce.
        </Vazio>
      ) : r.erro ? (
        <ErroBox erro={r.erro} aoTentar={r.recarregar} />
      ) : r.carregando && !r.dados ? (
        <Esqueleto linhas={6} />
      ) : diarios.length ? (
        <EmTransicao ativo={r.carregando}>
          {total != null && (
            <p className="kicker mb-3">
              {total.toLocaleString("pt-BR")} diários mencionam “{busca}”
            </p>
          )}
          <div className="flex flex-col gap-4">
            {diarios.map((d, i) => (
              <Card key={`${d.url}-${i}`} className="p-5">
                <div className="mb-2 flex flex-wrap items-baseline gap-x-3 gap-y-1">
                  <span className="num text-sm font-semibold text-ink">{formataData(d.data)}</span>
                  {d.edicao && <span className="num text-xs text-muted">edição {d.edicao}</span>}
                  {d.extra && (
                    <span className="num rounded-full bg-ocre/15 px-2 py-0.5 text-[0.65rem] uppercase tracking-wider text-ocre">
                      edição extra
                    </span>
                  )}
                  <span className="num text-xs text-muted">
                    {d.municipio}
                    {d.uf && `/${d.uf}`}
                  </span>
                </div>
                {d.trechos.map((t, j) => (
                  <blockquote
                    key={j}
                    className="mb-2 border-l-2 border-accent/40 pl-3 font-editorial text-sm italic leading-relaxed text-ink/80 wrap-anywhere"
                  >
                    …{t.trim()}…
                  </blockquote>
                ))}
                {/* via /api/arquivo: a fonte serve octet-stream e o celular
                    não abre; o proxy corrige o tipo e o visualizador nativo
                    (iOS/Android) assume */}
                <div className="mt-3 flex flex-wrap gap-2">
                  <a
                    href={`/api/arquivo?url=${encodeURIComponent(d.url)}&nome=${encodeURIComponent(
                      `diario-${d.municipio.toLowerCase().replace(/\s+/g, "-")}-${d.data ?? ""}.pdf`,
                    )}`}
                    target="_blank"
                    rel="noreferrer"
                    className="num inline-flex min-h-9 items-center rounded-md border border-accent px-3.5 py-1.5 text-xs uppercase tracking-wider text-accent transition-colors hover:bg-accent hover:text-surface"
                  >
                    abrir o diário (PDF) →
                  </a>
                  {d.url_texto && (
                    <a
                      href={`/api/arquivo?url=${encodeURIComponent(d.url_texto)}&nome=${encodeURIComponent(
                        `diario-${d.municipio.toLowerCase().replace(/\s+/g, "-")}-${d.data ?? ""}.txt`,
                      )}`}
                      target="_blank"
                      rel="noreferrer"
                      className="num inline-flex min-h-9 items-center rounded-md border border-line px-3.5 py-1.5 text-xs uppercase tracking-wider text-muted transition-colors hover:border-accent hover:text-accent"
                    >
                      texto puro
                    </a>
                  )}
                </div>
              </Card>
            ))}
          </div>
          <div className="mt-5 flex flex-wrap items-center gap-3 gap-y-2">
            <button
              onClick={() => setPagina((p) => Math.max(1, p - 1))}
              disabled={pagina <= 1}
              className="num rounded-md border border-line px-3 py-1 text-xs uppercase tracking-wider text-ink transition-colors hover:bg-surface-2 disabled:cursor-not-allowed disabled:opacity-40"
            >
              ← anteriores
            </button>
            <span className="num text-xs text-muted">página {pagina}</span>
            <button
              onClick={() => setPagina((p) => p + 1)}
              disabled={!temProxima}
              className="num rounded-md border border-line px-3 py-1 text-xs uppercase tracking-wider text-ink transition-colors hover:bg-surface-2 disabled:cursor-not-allowed disabled:opacity-40"
            >
              próximos →
            </button>
          </div>
        </EmTransicao>
      ) : (
        <Vazio>
          {aviso ??
            "nada encontrado; pode ser falta de cobertura da cidade ou o termo não aparece."}
        </Vazio>
      )}

      <SeloFonte
        fonte={
          fonte ?? {
            nome: "Querido Diário, Open Knowledge Brasil",
            url: "https://queridodiario.ok.org.br",
            nota: "Projeto da sociedade civil que liberta os diários oficiais municipais: coleta, extrai o texto e abre a busca.",
          }
        }
      />
    </div>
  );
}
