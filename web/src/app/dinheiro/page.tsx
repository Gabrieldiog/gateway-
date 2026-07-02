"use client";

import { useState } from "react";
import { CadernoHeader } from "@/components/Caderno";
import { Card } from "@/components/Card";
import { Carimbo } from "@/components/Carimbo";
import { Kpi } from "@/components/Kpi";
import { SeloFonte } from "@/components/SeloFonte";
import { Esqueleto, ErroBox, Vazio, EmTransicao } from "@/components/Estados";
import { useBalcao } from "@/hooks/useBalcao";
import { caminho, formataBRL, formataData, formataReaisCompacto } from "@/lib/api";
import { CAPITAIS, UFS } from "@/lib/ufs";
import type {
  BeneficioSocial,
  Emenda,
  FonteDado,
  Municipio,
  NormalizedResponse,
  Sancao,
} from "@/lib/types";

type Modo = "emendas" | "sancoes" | "bolsa";

const MODOS: [Modo, string][] = [
  ["emendas", "Emendas"],
  ["sancoes", "Sanções"],
  ["bolsa", "Bolsa Família"],
];

const ANOS = [2026, 2025, 2024];

// meses com folha fechada do Bolsa Família (a fonte publica com ~1 mês de atraso)
const MESES = [
  { valor: "202605", label: "mai/2026" },
  { valor: "202604", label: "abr/2026" },
  { valor: "202603", label: "mar/2026" },
  { valor: "202602", label: "fev/2026" },
  { valor: "202601", label: "jan/2026" },
  { valor: "202512", label: "dez/2025" },
];

const campo =
  "rounded-md border border-line bg-surface px-2 py-1.5 text-sm text-ink focus:border-accent focus:outline-none";

function Emendas() {
  const [ano, setAno] = useState(2026);
  const [autor, setAutor] = useState("");
  const [autorAplicado, setAutorAplicado] = useState("");
  const [pagina, setPagina] = useState(1);

  const r = useBalcao<NormalizedResponse<Emenda>>(
    caminho("transparencia/emendas", { ano, autor: autorAplicado || undefined, pagina }),
  );
  const emendas = r.dados?.dados ?? [];
  const temProxima = Boolean(r.dados?.meta?.tem_proxima);
  const fonte = r.dados?.meta?.fonte as FonteDado | undefined;

  return (
    <div>
      <form
        className="mb-5 flex flex-wrap items-center gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          setAutorAplicado(autor.trim());
          setPagina(1);
        }}
      >
        <div className="flex items-center gap-2">
          {ANOS.map((a) => (
            <button
              key={a}
              type="button"
              onClick={() => {
                setAno(a);
                setPagina(1);
              }}
              aria-pressed={a === ano}
              className={`num rounded-full border px-3 py-1 text-xs uppercase tracking-wider transition-colors ${
                a === ano
                  ? "border-accent bg-accent text-surface"
                  : "border-line text-muted hover:border-accent hover:text-accent"
              }`}
            >
              {a}
            </button>
          ))}
        </div>
        <input
          value={autor}
          onChange={(e) => setAutor(e.target.value)}
          placeholder="filtrar por autor (ex: bancada)"
          className={`${campo} w-64`}
        />
        <button
          type="submit"
          className="num rounded-md border border-ink/20 px-3 py-1.5 text-xs uppercase tracking-wider text-ink transition-colors hover:bg-surface-2"
        >
          filtrar
        </button>
        <Carimbo fonte="CGU" ms={r.ms} erro={!!r.erro} />
      </form>

      {r.erro ? (
        <ErroBox erro={r.erro} aoTentar={r.recarregar} />
      ) : r.carregando && !r.dados ? (
        <Esqueleto linhas={8} />
      ) : emendas.length ? (
        <EmTransicao ativo={r.carregando}>
          <Card className="divide-y divide-line p-0">
            {emendas.map((e) => (
              <div key={e.codigo} className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 px-5 py-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-ink" title={e.autor}>
                    {e.autor}
                  </p>
                  <p className="num mt-0.5 text-xs text-muted">
                    {[e.funcao, e.localidade].filter(Boolean).join(" · ")}
                  </p>
                </div>
                <div className="text-right">
                  <p className="num text-sm text-ink">
                    {e.valor_empenhado ? formataReaisCompacto(e.valor_empenhado) : "—"}
                    <span className="ml-1 text-xs text-muted">empenhado</span>
                  </p>
                  <p className="num text-xs text-muted">
                    pago {e.valor_pago ? formataReaisCompacto(e.valor_pago) : "—"}
                  </p>
                </div>
              </div>
            ))}
          </Card>
          <div className="mt-4 flex items-center gap-3">
            <button
              onClick={() => setPagina((p) => Math.max(1, p - 1))}
              disabled={pagina <= 1}
              className="num rounded-md border border-line px-3 py-1 text-xs uppercase tracking-wider text-ink transition-colors hover:bg-surface-2 disabled:opacity-40"
            >
              ← anterior
            </button>
            <span className="num text-xs text-muted">página {pagina}</span>
            <button
              onClick={() => setPagina((p) => p + 1)}
              disabled={!temProxima}
              className="num rounded-md border border-line px-3 py-1 text-xs uppercase tracking-wider text-ink transition-colors hover:bg-surface-2 disabled:opacity-40"
            >
              próxima →
            </button>
          </div>
        </EmTransicao>
      ) : (
        <Vazio>nenhuma emenda encontrada com esses filtros.</Vazio>
      )}
      <SeloFonte fonte={fonte} />
    </div>
  );
}

function Sancoes() {
  const [documento, setDocumento] = useState("");
  const [consultado, setConsultado] = useState("");

  const r = useBalcao<NormalizedResponse<Sancao>>(
    consultado ? caminho("transparencia/sancoes", { documento: consultado }) : null,
  );
  const sancoes = r.dados?.dados ?? [];
  const fonte = r.dados?.meta?.fonte as FonteDado | undefined;

  return (
    <div>
      <form
        className="mb-5 flex flex-wrap items-center gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          setConsultado(documento.trim());
        }}
      >
        <input
          value={documento}
          onChange={(e) => setDocumento(e.target.value)}
          placeholder="CNPJ ou CPF (com ou sem máscara)"
          className={`${campo} w-72`}
        />
        <button
          type="submit"
          className="num rounded-md border border-accent bg-accent px-4 py-1.5 text-xs uppercase tracking-wider text-surface transition-opacity hover:opacity-90"
        >
          consultar
        </button>
        {consultado && <Carimbo fonte="CGU" ms={r.ms} erro={!!r.erro} />}
      </form>

      {!consultado ? (
        <Vazio>
          digite um CNPJ ou CPF pra saber se está no CEIS (impedidos de contratar) ou no CNEP
          (punidos pela Lei Anticorrupção).
        </Vazio>
      ) : r.erro ? (
        <ErroBox erro={r.erro} aoTentar={r.recarregar} />
      ) : r.carregando && !r.dados ? (
        <Esqueleto linhas={4} />
      ) : sancoes.length ? (
        <EmTransicao ativo={r.carregando}>
          <div className="flex flex-col gap-3">
            {sancoes.map((s, i) => (
              <Card key={`${s.cadastro}-${i}`} className="p-4 pt-5">
                <div className="flex flex-wrap items-baseline justify-between gap-2 pl-4">
                  <p className="text-sm font-semibold text-ink">{s.sancionado}</p>
                  <span className="num rounded-full bg-erro/10 px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wider text-erro">
                    {s.cadastro}
                  </span>
                </div>
                {s.tipo && <p className="mt-1.5 pl-4 font-editorial text-sm text-ink/80">{s.tipo}</p>}
                <p className="num mt-2 pl-4 text-xs text-muted">
                  {[s.orgao, s.uf, s.esfera].filter(Boolean).join(" · ")}
                  {s.inicio && (
                    <span className="ml-2 text-ink">
                      {formataData(s.inicio)} → {s.fim ? formataData(s.fim) : "sem prazo"}
                    </span>
                  )}
                </p>
              </Card>
            ))}
          </div>
        </EmTransicao>
      ) : (
        <Card className="p-5 pl-9">
          <p className="font-editorial text-lg text-ink">
            Nada consta. <span className="text-muted">Esse documento não aparece no CEIS nem no CNEP.</span>
          </p>
        </Card>
      )}
      <SeloFonte fonte={fonte} />
    </div>
  );
}

function BolsaFamilia() {
  const [uf, setUf] = useState("GO");
  const [ibge, setIbge] = useState(CAPITAIS.GO);
  const [mes, setMes] = useState(MESES[0].valor);

  const cidades = useBalcao<NormalizedResponse<Municipio>>(
    caminho("ibge/municipios", { uf }),
  );
  const r = useBalcao<NormalizedResponse<BeneficioSocial>>(
    caminho("transparencia/bolsa-familia", { municipio: ibge, mes }),
  );
  const folha = r.dados?.dados?.[0];
  const fonte = r.dados?.meta?.fonte as FonteDado | undefined;
  const media =
    folha && folha.beneficiarios ? Number(folha.valor) / folha.beneficiarios : null;

  return (
    <div>
      <div className="mb-5 flex flex-wrap items-center gap-3">
        <select
          value={uf}
          onChange={(e) => {
            setUf(e.target.value);
            setIbge(CAPITAIS[e.target.value]);
          }}
          className={campo}
          aria-label="estado"
        >
          {UFS.map((u) => (
            <option key={u}>{u}</option>
          ))}
        </select>
        <select
          value={ibge}
          onChange={(e) => setIbge(e.target.value)}
          className={`${campo} max-w-56`}
          aria-label="cidade"
        >
          {(cidades.dados?.dados ?? []).map((m) => (
            <option key={m.id} value={String(m.id)}>
              {m.nome}
            </option>
          ))}
        </select>
        <select value={mes} onChange={(e) => setMes(e.target.value)} className={campo} aria-label="mês">
          {MESES.map((m) => (
            <option key={m.valor} value={m.valor}>
              {m.label}
            </option>
          ))}
        </select>
        <Carimbo fonte="CGU" ms={r.ms} erro={!!r.erro} />
      </div>

      {r.erro ? (
        <ErroBox erro={r.erro} aoTentar={r.recarregar} />
      ) : r.carregando && !r.dados ? (
        <Esqueleto linhas={4} />
      ) : folha ? (
        <EmTransicao ativo={r.carregando}>
          <Card className="p-6">
            <p className="kicker mb-4 pl-4">
              {folha.programa} · {folha.municipio}/{folha.uf}
            </p>
            <div className="flex flex-wrap gap-x-12 gap-y-5 pl-4">
              <Kpi rotulo="famílias atendidas" valor={folha.beneficiarios ?? 0} tom="accent-2" />
              <div className="flex flex-col">
                <span className="kicker mb-1">total pago no mês</span>
                <span className="font-display text-4xl font-semibold leading-none tracking-tight text-ink sm:text-5xl">
                  {formataReaisCompacto(folha.valor)}
                </span>
              </div>
              {media != null && (
                <div className="flex flex-col">
                  <span className="kicker mb-1">média por família</span>
                  <span className="font-display text-4xl font-semibold leading-none tracking-tight text-ink sm:text-5xl">
                    {formataBRL(media)}
                  </span>
                </div>
              )}
            </div>
          </Card>
        </EmTransicao>
      ) : (
        <Vazio>sem folha publicada pra esse município nesse mês.</Vazio>
      )}
      <SeloFonte fonte={fonte} />
    </div>
  );
}

export default function CadernoDinheiro() {
  const [modo, setModo] = useState<Modo>("emendas");

  return (
    <div>
      <CadernoHeader
        numero="XVII"
        kicker="Portal da Transparência · CGU"
        titulo="Dinheiro público"
        resumo="Pra onde vai o dinheiro federal: as emendas que cada parlamentar destinou, as empresas e pessoas punidas pelo poder público, e quanto o Bolsa Família paga em cada cidade. Direto da Controladoria-Geral da União."
      />

      <div className="mb-6 inline-flex gap-0.5 rounded-md border border-line p-0.5">
        {MODOS.map(([v, label]) => (
          <button
            key={v}
            onClick={() => setModo(v)}
            aria-pressed={modo === v}
            className={`num rounded px-3 py-1 text-xs uppercase tracking-wider transition-colors ${
              modo === v ? "bg-accent/15 font-semibold text-accent" : "text-muted hover:text-ink"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {modo === "emendas" && <Emendas />}
      {modo === "sancoes" && <Sancoes />}
      {modo === "bolsa" && <BolsaFamilia />}
    </div>
  );
}
