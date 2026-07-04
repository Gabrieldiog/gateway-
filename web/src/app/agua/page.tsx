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
import { caminho, formataData } from "@/lib/api";
import { UFS } from "@/lib/ufs";
import type { FonteDado, MedicaoReservatorio, NormalizedResponse, Reservatorio } from "@/lib/types";

const SISTEMAS: [string, string][] = [
  ["sin", "Hidrelétricas (SIN)"],
  ["nordeste", "Açudes do Nordeste"],
  ["cantareira", "Cantareira (SP)"],
];

const SUGESTOES: { rotulo: string; sistema: string; codigo: string }[] = [
  { rotulo: "Cantareira (SP)", sistema: "cantareira", codigo: "29001" },
  { rotulo: "Sobradinho (BA)", sistema: "sin", codigo: "19121" },
  { rotulo: "Castanhão (CE)", sistema: "nordeste", codigo: "12112" },
];

function corDoNivel(pct: number): string {
  if (pct >= 70) return "text-ok";
  if (pct >= 40) return "text-ocre";
  return "text-erro";
}

function NivelBarra({ pct }: { pct: number }) {
  const cor = pct >= 70 ? "bg-ok" : pct >= 40 ? "bg-ocre" : "bg-erro";
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-2">
      <div className={`h-full rounded-full ${cor}`} style={{ width: `${Math.min(100, pct)}%` }} />
    </div>
  );
}

// enchendo ou esvaziando? só dá pra saber quando a fonte informa os dois lados
function Tendencia({ m }: { m: MedicaoReservatorio }) {
  if (m.afluencia == null || m.defluencia == null) return null;
  if (m.afluencia > m.defluencia) return <span className="text-ok">enchendo ▲</span>;
  if (m.afluencia < m.defluencia) return <span className="text-muted">baixando ▽</span>;
  return <span className="text-muted">estável</span>;
}

function CartaoMedicao({ m, grande = false }: { m: MedicaoReservatorio; grande?: boolean }) {
  return (
    <Card className={grande ? "p-5" : "p-4"}>
      <p className="kicker">{m.sistema === "cantareira" ? "cantareira · sp" : m.sistema === "nordeste" ? "nordeste" : "sin"}</p>
      <h3 className={`font-display font-semibold leading-snug text-ink ${grande ? "text-xl" : "text-base"}`}>
        {m.reservatorio}
      </h3>
      {m.volume_util_pct != null ? (
        <>
          <p className={`num mt-1.5 font-semibold ${grande ? "text-4xl" : "text-2xl"} ${corDoNivel(m.volume_util_pct)}`}>
            {m.volume_util_pct.toLocaleString("pt-BR")}%
          </p>
          <div className="mt-1.5">
            <NivelBarra pct={m.volume_util_pct} />
          </div>
        </>
      ) : (
        <p className="mt-1.5 font-editorial text-sm italic text-muted">
          a fonte não informa o percentual — acompanhe pela cota e pela evolução abaixo.
        </p>
      )}
      <div className="num mt-2 flex flex-wrap gap-x-4 gap-y-0.5 text-xs text-muted">
        <Tendencia m={m} />
        {m.cota != null && <span>cota {m.cota.toLocaleString("pt-BR")} m</span>}
        {m.afluencia != null && <span>entra {m.afluencia.toLocaleString("pt-BR")} m³/s</span>}
        {m.defluencia != null && <span>sai {m.defluencia.toLocaleString("pt-BR")} m³/s</span>}
        {m.data && <span>medido em {formataData(m.data)}</span>}
      </div>
    </Card>
  );
}

// os últimos 30 dias em barras — % quando a fonte dá, senão a cota (normalizada)
function Evolucao({ codigo }: { codigo: string }) {
  const r = useBalcao<NormalizedResponse<MedicaoReservatorio>>(
    caminho("ana/historico", { codigo, dias: 30 }),
  );
  const medidas = r.dados?.dados ?? [];

  if (r.erro) return <ErroBox erro={r.erro} aoTentar={r.recarregar} />;
  if (r.carregando && !r.dados) return <Esqueleto linhas={3} />;
  if (!medidas.length) {
    return (
      <p className="font-editorial text-sm italic text-muted">
        sem medições no último mês — açude pequeno pode passar meses sem informar.
      </p>
    );
  }

  const usaPct = medidas.some((m) => m.volume_util_pct != null);
  const serie = medidas
    .map((m) => ({ data: m.data, valor: usaPct ? m.volume_util_pct : m.cota }))
    .filter((p): p is { data: string | null; valor: number } => p.valor != null);
  if (!serie.length) return <Vazio>a fonte não trouxe valores nesse período.</Vazio>;

  const min = Math.min(...serie.map((p) => p.valor));
  const max = Math.max(...serie.map((p) => p.valor));
  const altura = (v: number) => {
    if (usaPct) return Math.max(4, v); // percentual em escala absoluta 0–100
    if (max === min) return 60;
    return 15 + ((v - min) / (max - min)) * 85; // cota: escala do período
  };
  const primeiro = serie[0];
  const ultimo = serie[serie.length - 1];
  const rotulo = (v: number) => (usaPct ? `${v.toLocaleString("pt-BR")}%` : `cota ${v.toLocaleString("pt-BR")} m`);

  return (
    <div>
      <p className="kicker mb-2">últimos 30 dias · {usaPct ? "volume útil" : "cota (escala do período)"}</p>
      <div className="flex h-20 items-end gap-[2px]">
        {serie.map((p, i) => (
          <div
            key={i}
            title={`${p.data ? formataData(p.data) : ""}: ${rotulo(p.valor)}`}
            className="min-w-0 flex-1 rounded-t-sm bg-accent-2/50 transition-colors hover:bg-accent-2"
            style={{ height: `${altura(p.valor)}%` }}
          />
        ))}
      </div>
      <div className="num mt-1.5 flex justify-between text-xs text-muted">
        <span>
          {primeiro.data && formataData(primeiro.data)} · {rotulo(primeiro.valor)}
        </span>
        <span className="text-ink">
          {ultimo.data && formataData(ultimo.data)} · {rotulo(ultimo.valor)}
        </span>
      </div>
    </div>
  );
}

function ReservatorioEscolhido({ codigo }: { codigo: string }) {
  const r = useBalcao<NormalizedResponse<MedicaoReservatorio>>(caminho("ana/agora", { codigo }));
  const m = r.dados?.dados?.[0];

  if (r.erro) return <ErroBox erro={r.erro} aoTentar={r.recarregar} />;
  if (r.carregando && !r.dados) return <Esqueleto linhas={4} />;
  if (!m) return <Vazio>a ANA não tem medição registrada pra esse reservatório.</Vazio>;

  return (
    <EmTransicao ativo={r.carregando}>
      <div className="flex flex-col gap-4">
        <CartaoMedicao m={m} grande />
        <Card className="p-5">
          <Evolucao codigo={codigo} />
        </Card>
      </div>
    </EmTransicao>
  );
}

export default function CadernoAgua() {
  const [sistema, setSistema] = useState("sin");
  const [uf, setUf] = useState("");
  const [codigo, setCodigo] = useState("");

  const principais = useBalcao<NormalizedResponse<MedicaoReservatorio>>(caminho("ana/principais"));
  const lista = useBalcao<NormalizedResponse<Reservatorio>>(
    caminho("ana/reservatorios", { sistema, uf: sistema === "nordeste" ? uf || undefined : undefined }),
  );
  const grandes = principais.dados?.dados ?? [];
  const opcoes = lista.dados?.dados ?? [];
  const fonte = principais.dados?.meta?.fonte as FonteDado | undefined;

  return (
    <div>
      <CadernoHeader
        numero="XXXI"
        kicker="ANA · Sala de Situação"
        titulo="Água"
        resumo="Quanta água tem nos reservatórios do país — das hidrelétricas que acendem a luz aos açudes do Semiárido e ao Cantareira que abastece São Paulo. Medição diária informada à ANA, reservatório por reservatório."
      />

      <section className="mb-10">
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <h2 className="font-display text-lg font-semibold text-ink">Os grandes do país</h2>
          <Carimbo
            fonte="ANA"
            cache={principais.dados?.meta?.cache as string | undefined}
            ms={principais.ms}
            erro={!!principais.erro}
          />
        </div>
        <p className="mb-4 max-w-2xl font-editorial text-sm leading-relaxed text-ink/75">
          O número grande é o <Termo t="volumeutil">volume útil</Termo>: quanto da água aproveitável
          ainda está lá. Verde é folga, ocre é atenção, vermelho é seca. E a seta diz se a{" "}
          <Termo t="afluencia">afluência</Termo> está vencendo a <Termo t="defluencia">defluência</Termo> —
          ou seja, se o reservatório enche ou baixa.
        </p>
        {principais.erro ? (
          <ErroBox erro={principais.erro} aoTentar={principais.recarregar} />
        ) : principais.carregando && !principais.dados ? (
          <Esqueleto linhas={6} />
        ) : grandes.length ? (
          <EmTransicao ativo={principais.carregando}>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {grandes.map((m) => (
                <CartaoMedicao key={m.codigo} m={m} />
              ))}
            </div>
          </EmTransicao>
        ) : (
          <Vazio>nenhuma medição disponível agora.</Vazio>
        )}
      </section>

      <section>
        <h2 className="mb-1 font-display text-lg font-semibold text-ink">Procure o seu</h2>
        <p className="mb-4 max-w-2xl font-editorial text-sm leading-relaxed text-ink/75">
          São mais de 700 reservatórios monitorados. Escolha o sistema e ache o que abastece a sua
          região — a <Termo t="cota">cota</Termo> e a evolução dos últimos 30 dias vêm juntas.
        </p>
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <div className="-mx-1 overflow-x-auto px-1">
            <div className="inline-flex gap-0.5 rounded-md border border-line p-0.5">
              {SISTEMAS.map(([v, label]) => (
                <button
                  key={v}
                  onClick={() => {
                    setSistema(v);
                    setUf("");
                    setCodigo("");
                  }}
                  aria-pressed={sistema === v}
                  className={`num shrink-0 whitespace-nowrap rounded px-3 py-1 text-xs uppercase tracking-wider transition-colors ${
                    sistema === v ? "bg-accent/15 font-semibold text-accent" : "text-muted hover:text-ink"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
          {sistema === "nordeste" && (
            <Seletor
              value={uf}
              onChange={(e) => {
                setUf(e.target.value);
                setCodigo("");
              }}
              aria-label="estado"
            >
              <option value="">todos os estados</option>
              {UFS.map((u) => (
                <option key={u}>{u}</option>
              ))}
            </Seletor>
          )}
          <Seletor value={codigo} onChange={(e) => setCodigo(e.target.value)} aria-label="reservatório">
            <option value="">
              {lista.carregando ? "carregando a lista…" : `escolha (${opcoes.length} na lista)`}
            </option>
            {opcoes.map((o) => (
              <option key={o.codigo} value={o.codigo}>
                {o.nome}
                {o.uf ? ` (${o.uf})` : ""}
              </option>
            ))}
          </Seletor>
        </div>
        <div className="mb-5 flex flex-wrap items-center gap-2">
          <span className="kicker">experimente:</span>
          {SUGESTOES.map((s) => (
            <button
              key={s.codigo}
              onClick={() => {
                setSistema(s.sistema);
                setUf("");
                setCodigo(s.codigo);
              }}
              className="num rounded-full border border-line px-3 py-1 text-xs text-ink transition-colors hover:border-accent hover:text-accent"
            >
              {s.rotulo}
            </button>
          ))}
        </div>

        {codigo ? (
          <ReservatorioEscolhido codigo={codigo} />
        ) : lista.erro ? (
          <ErroBox erro={lista.erro} aoTentar={lista.recarregar} />
        ) : (
          <Vazio>escolha um reservatório na lista — ou toque numa sugestão.</Vazio>
        )}
      </section>

      <SeloFonte fonte={fonte} />
    </div>
  );
}
