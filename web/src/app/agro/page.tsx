"use client";

import { useState } from "react";
import { CadernoHeader } from "@/components/Caderno";
import { Card } from "@/components/Card";
import { Carimbo } from "@/components/Carimbo";
import { Seletor } from "@/components/Seletor";
import { SeloFonte } from "@/components/SeloFonte";
import { Esqueleto, ErroBox, Vazio, EmTransicao } from "@/components/Estados";
import { BadgeFrescor } from "@/components/Frescor";
import { useBalcao } from "@/hooks/useBalcao";
import { caminho } from "@/lib/api";
import { anos, rotuloMesAAAAMM } from "@/lib/datas";
import { UFS } from "@/lib/ufs";
import type {
  Abate,
  Leite,
  PrecoAgro,
  SafraConab,
  SafraMensal,
} from "@/lib/types";
import type { IndicadorAgro, NormalizedResponse } from "@/lib/types";

const FONTE_SIDRA = {
  nome: "IBGE — SIDRA (PAM e PPM)",
  url: "https://sidra.ibge.gov.br/",
  nota: "Produção Agrícola Municipal e Pesquisa da Pecuária Municipal do IBGE. O SIDRA fala em códigos de tabela — o Balcão traduz e devolve o ranking pronto.",
};

const PRODUTOS: [string, string][] = [
  ["soja", "soja"], ["milho", "milho"], ["cana", "cana-de-açúcar"], ["algodao", "algodão"],
  ["arroz", "arroz"], ["feijao", "feijão"], ["trigo", "trigo"], ["mandioca", "mandioca"],
];
const ANIMAIS: [string, string][] = [
  ["bovino", "bovino"], ["suino", "suíno"], ["galinaceos", "galináceos"], ["equino", "equino"],
  ["caprino", "caprino"], ["ovino", "ovino"], ["bubalino", "bubalino"], ["codorna", "codorna"],
];
const VARIAVEIS: [string, string][] = [["quantidade", "quantidade"], ["area", "área plantada"]];

function compacto(valor: number, unidade: string | null): string {
  const n = new Intl.NumberFormat("pt-BR", { notation: "compact", maximumFractionDigits: 1 }).format(valor);
  const u =
    unidade === "Toneladas" ? "t" : unidade === "Hectares" ? "ha" : unidade === "Cabeças" ? "cab." : unidade ?? "";
  return `${n} ${u}`.trim();
}

const num = (v: number | null | undefined, casas = 1) =>
  v == null ? "—" : new Intl.NumberFormat("pt-BR", { notation: "compact", maximumFractionDigits: casas }).format(v);

const FONTE_LSPA = {
  nome: "IBGE — LSPA (safra em curso)",
  url: "https://sidra.ibge.gov.br/pesquisa/lspa",
  nota: "A estimativa oficial da safra deste ano, revisada todo mês. É previsão que amadurece: os números se ajustam a cada levantamento.",
};

const FONTE_CONAB = {
  nome: "CONAB — Companhia Nacional de Abastecimento",
  url: "https://portaldeinformacoes.conab.gov.br",
  nota: "Levantamentos de safra e preços agropecuários da CONAB, atualizados diariamente a partir dos arquivos oficiais.",
};

const PRODUTOS_LSPA: [string, string][] = [
  ["soja", "Soja"], ["milho1", "Milho 1ª"], ["milho2", "Milho 2ª"], ["arroz", "Arroz"],
  ["trigo", "Trigo"], ["cafe", "Café"], ["cana", "Cana"], ["algodao", "Algodão"],
];

function ChipsProduto({
  opcoes,
  valor,
  aoMudar,
}: {
  opcoes: [string, string][];
  valor: string;
  aoMudar: (v: string) => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      {opcoes.map(([v, label]) => (
        <button
          key={v}
          onClick={() => aoMudar(v)}
          aria-pressed={v === valor}
          className={`num rounded-full border px-3 py-1 text-xs uppercase tracking-wider transition-colors ${
            v === valor
              ? "border-accent bg-accent text-surface"
              : "border-line text-muted hover:border-accent hover:text-accent"
          }`}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

// a safra que está no campo AGORA: a estimativa mensal do IBGE pro produto
// escolhido, lado a lado com o levantamento da CONAB
function SafraAgora() {
  const [produto, setProduto] = useState("soja");
  const lspa = useBalcao<NormalizedResponse<SafraMensal>>(caminho("sidra/safra", { produto }));
  const conab = useBalcao<NormalizedResponse<SafraConab>>(caminho("conab/safra"));
  const s = lspa.dados?.dados?.[0];
  const mes = lspa.dados?.meta?.mes as string | undefined;
  const topo = (conab.dados?.dados ?? []).slice(0, 5);
  const anoAgricola = conab.dados?.meta?.ano_agricola as string | undefined;
  const levantamento = conab.dados?.meta?.levantamento as string | undefined;

  return (
    <section>
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="kicker mb-1 text-accent">no campo agora</p>
          <h2 className="font-display text-2xl font-semibold tracking-tight text-ink">
            A safra deste ano
          </h2>
        </div>
        <Carimbo fonte="LSPA" cache={lspa.dados?.meta?.cache as string | undefined} ms={lspa.ms} erro={!!lspa.erro} />
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-x-4 gap-y-3">
        <ChipsProduto opcoes={PRODUTOS_LSPA} valor={produto} aoMudar={setProduto} />
        <BadgeFrescor
          rotulo="estimativa mensal"
          detalhe={mes ? `levantamento de ${rotuloMesAAAAMM(mes)} · os números amadurecem` : undefined}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.2fr_1fr]">
        <Card className="p-5 pt-6">
          {lspa.erro ? (
            <ErroBox erro={lspa.erro} aoTentar={lspa.recarregar} />
          ) : lspa.carregando && !lspa.dados ? (
            <Esqueleto linhas={4} />
          ) : s ? (
            <EmTransicao ativo={lspa.carregando}>
              <div className="flex flex-wrap gap-x-10 gap-y-4 pl-4">
                <div>
                  <p className="kicker mb-1">produção estimada</p>
                  <p className="num font-display text-4xl font-semibold leading-none tracking-tight text-accent-2 sm:text-5xl">
                    {num(s.producao_t)} t
                  </p>
                </div>
                <div>
                  <p className="kicker mb-1">área plantada</p>
                  <p className="num font-display text-3xl font-semibold leading-none tracking-tight text-ink">
                    {num(s.area_plantada_ha)} ha
                  </p>
                </div>
                <div>
                  <p className="kicker mb-1">rendimento</p>
                  <p className="num font-display text-3xl font-semibold leading-none tracking-tight text-ink">
                    {s.rendimento_kg_ha ? `${s.rendimento_kg_ha.toLocaleString("pt-BR")} kg/ha` : "—"}
                  </p>
                </div>
              </div>
            </EmTransicao>
          ) : (
            <Vazio>o LSPA ainda não tem estimativa pra esse produto.</Vazio>
          )}
        </Card>

        <Card className="p-5 pt-6">
          <p className="kicker mb-3 pl-4">
            visão CONAB{anoAgricola && ` · safra ${anoAgricola}`}{levantamento && ` · ${levantamento.toLowerCase()}`}
          </p>
          {conab.erro ? (
            <ErroBox erro={conab.erro} aoTentar={conab.recarregar} />
          ) : conab.carregando && !conab.dados ? (
            <Esqueleto linhas={4} />
          ) : (
            <ol className="flex flex-col gap-1.5 pl-4">
              {topo.map((c) => (
                <li key={c.produto} className="flex items-baseline justify-between gap-3">
                  <span className="truncate text-sm text-ink/85">{c.produto}</span>
                  <span className="num shrink-0 text-sm text-ink">
                    {num((c.producao_mil_t ?? 0) * 1000)} t
                  </span>
                </li>
              ))}
            </ol>
          )}
        </Card>
      </div>
      <SeloFonte fonte={FONTE_LSPA} />
    </section>
  );
}

// o trimestre da proteína: quantos animais viraram carne e quanto leite
// chegou aos laticínios — com o preço pago na porteira
function AbateLeite() {
  const bois = useBalcao<NormalizedResponse<Abate>>(caminho("sidra/abate", { tipo: "bovino" }));
  const suinos = useBalcao<NormalizedResponse<Abate>>(caminho("sidra/abate", { tipo: "suino" }));
  const frangos = useBalcao<NormalizedResponse<Abate>>(caminho("sidra/abate", { tipo: "frango" }));
  const leite = useBalcao<NormalizedResponse<Leite>>(caminho("sidra/leite"));
  const tri =
    bois.dados?.dados?.[0]?.trimestre ?? leite.dados?.dados?.[0]?.trimestre ?? null;
  const l = leite.dados?.dados?.[0];

  const cartoes = [
    { rotulo: "bovinos abatidos", r: bois },
    { rotulo: "suínos abatidos", r: suinos },
    { rotulo: "frangos abatidos", r: frangos },
  ];

  return (
    <section>
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="kicker mb-1 text-accent-2">abate e leite</p>
          <h2 className="font-display text-2xl font-semibold tracking-tight text-ink">
            O trimestre da proteína{tri && <span className="text-muted"> · {tri}</span>}
          </h2>
        </div>
        <Carimbo fonte="IBGE" ms={bois.ms} erro={!!bois.erro} />
      </div>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {cartoes.map(({ rotulo, r }) => {
          const a = r.dados?.dados?.[0];
          return (
            <Card key={rotulo} className="p-4 pt-5">
              <p className="kicker mb-2 pl-4">{rotulo}</p>
              {r.erro ? (
                <p className="pl-4 text-xs text-erro">indisponível</p>
              ) : r.carregando && !a ? (
                <Esqueleto linhas={1} />
              ) : (
                <p className="num pl-4 font-display text-3xl font-semibold leading-none tracking-tight text-ink">
                  {num(a?.animais ?? null)}
                </p>
              )}
            </Card>
          );
        })}
        <Card className="p-4 pt-5">
          <p className="kicker mb-2 pl-4">leite · preço ao produtor</p>
          {leite.erro ? (
            <p className="pl-4 text-xs text-erro">indisponível</p>
          ) : leite.carregando && !l ? (
            <Esqueleto linhas={1} />
          ) : (
            <>
              <p className="num pl-4 font-display text-3xl font-semibold leading-none tracking-tight text-accent">
                {l?.preco_medio ? `R$ ${l.preco_medio.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}` : "—"}
                <span className="ml-1 text-base font-normal text-muted">/litro</span>
              </p>
              <p className="num mt-1.5 pl-4 text-xs text-muted">{num(l?.litros ?? null)} litros captados</p>
            </>
          )}
        </Card>
      </div>
    </section>
  );
}

const PRODUTOS_PRECO: [string, string][] = [
  ["soja", "Soja"], ["milho", "Milho"], ["arroz", "Arroz"],
  ["trigo", "Trigo"], ["feijao", "Feijão"], ["algodao", "Algodão"],
];

// o preço que o produtor recebe, estado a estado, no mês mais novo que a
// CONAB apurou pra cada UF
function PrecoPorteira() {
  const [produto, setProduto] = useState("soja");
  const r = useBalcao<NormalizedResponse<PrecoAgro>>(caminho("conab/precos", { produto }));
  const linhas = r.dados?.dados ?? [];
  const max = linhas.length ? linhas[0].valor_kg ?? 1 : 1;

  return (
    <section>
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="kicker mb-1 text-ocre">na porteira</p>
          <h2 className="font-display text-2xl font-semibold tracking-tight text-ink">
            O preço pago ao produtor
          </h2>
        </div>
        <Carimbo fonte="CONAB" cache={r.dados?.meta?.cache as string | undefined} ms={r.ms} erro={!!r.erro} />
      </div>
      <div className="mb-4">
        <ChipsProduto opcoes={PRODUTOS_PRECO} valor={produto} aoMudar={setProduto} />
      </div>
      {r.erro ? (
        <ErroBox erro={r.erro} aoTentar={r.recarregar} />
      ) : r.carregando && !r.dados ? (
        <Esqueleto linhas={8} />
      ) : linhas.length ? (
        <EmTransicao ativo={r.carregando}>
          <Card className="p-5 sm:p-6">
            <ul className="flex flex-col gap-2.5">
              {linhas.map((p, i) => (
                <li key={p.uf}>
                  <div className="mb-1 flex items-baseline justify-between gap-3">
                    <span className="num text-sm text-ink/85">
                      {p.uf}
                      <span className="ml-2 text-xs text-muted">{p.periodo}</span>
                    </span>
                    <span className={`num shrink-0 text-sm ${i === 0 ? "text-accent" : "text-ink"}`}>
                      R$ {(p.valor_kg ?? 0).toLocaleString("pt-BR", { minimumFractionDigits: 2 })}/kg
                    </span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-sm bg-surface-2">
                    <div
                      className="h-full rounded-sm bg-ocre/80"
                      style={{ width: `${Math.max(((p.valor_kg ?? 0) / max) * 100, 2)}%` }}
                    />
                  </div>
                </li>
              ))}
            </ul>
            <p className="mt-5 border-t border-line pt-3 font-editorial text-sm italic text-muted">
              Preço médio por kg pago ao produtor, no mês mais recente que a CONAB apurou em cada
              estado (a data acompanha cada linha).
            </p>
          </Card>
        </EmTransicao>
      ) : (
        <Vazio>a CONAB não tem preço recente pra esse produto.</Vazio>
      )}
      <SeloFonte fonte={FONTE_CONAB} />
    </section>
  );
}

const PRODUTOS_MUNICIPIO: [string, string][] = [
  ["soja", "Soja"], ["milho", "Milho"], ["cafe", "Café"], ["cana", "Cana"],
];

// os municípios que mais produzem — o zoom que o ranking por estado não dá
function MunicipiosCampeoes() {
  const [produto, setProduto] = useState("soja");
  const [uf, setUf] = useState("MT");
  const r = useBalcao<NormalizedResponse<IndicadorAgro>>(
    caminho("sidra/municipios", { produto, uf, limit: 10 }),
  );
  const linhas = (r.dados?.dados ?? []).filter((d) => d.valor != null);
  const max = linhas[0]?.valor ?? 1;
  const ano = r.dados?.meta?.ano as number | undefined;

  return (
    <section>
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="kicker mb-1 text-accent">o zoom</p>
          <h2 className="font-display text-2xl font-semibold tracking-tight text-ink">
            Municípios campeões{ano && <span className="text-muted"> · {ano}</span>}
          </h2>
        </div>
        <Carimbo fonte="SIDRA" cache={r.dados?.meta?.cache as string | undefined} ms={r.ms} erro={!!r.erro} />
      </div>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <ChipsProduto opcoes={PRODUTOS_MUNICIPIO} valor={produto} aoMudar={setProduto} />
        <Filtro rotulo="UF" valor={uf} aoMudar={setUf} opcoes={UFS.map((u) => [u, u])} />
      </div>
      {r.erro ? (
        <ErroBox erro={r.erro} aoTentar={r.recarregar} />
      ) : r.carregando && !r.dados ? (
        <Esqueleto linhas={6} />
      ) : linhas.length ? (
        <EmTransicao ativo={r.carregando}>
          <Card className="p-5 sm:p-6">
            <ol className="flex flex-col gap-2.5">
              {linhas.map((d, i) => (
                <li key={d.localidade_id ?? d.localidade}>
                  <div className="mb-1 flex items-baseline justify-between gap-3">
                    <span className="truncate text-sm text-ink/85">
                      <span className="num mr-2 text-xs text-muted">{i + 1}</span>
                      {d.localidade}
                    </span>
                    <span className={`num shrink-0 text-sm ${i === 0 ? "text-accent" : "text-ink"}`}>
                      {compacto(d.valor ?? 0, d.unidade)}
                    </span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-sm bg-surface-2">
                    <div
                      className={`h-full rounded-sm ${i === 0 ? "bg-accent" : "bg-accent-2/70"}`}
                      style={{ width: `${Math.max(((d.valor ?? 0) / max) * 100, 1.5)}%` }}
                    />
                  </div>
                </li>
              ))}
            </ol>
          </Card>
        </EmTransicao>
      ) : (
        <Vazio>sem dado municipal pra essa combinação.</Vazio>
      )}
    </section>
  );
}

export default function CadernoAgro() {
  const [modo, setModo] = useState<"producao" | "rebanho">("producao");
  const [produto, setProduto] = useState("soja");
  const [animal, setAnimal] = useState("bovino");
  const [variavel, setVariavel] = useState("quantidade");
  // null = "o mais recente que o IBGE publicou" — quem decide é o gateway
  const [ano, setAno] = useState<number | null>(null);

  const url =
    modo === "producao"
      ? caminho("sidra/producao", { produto, variavel, ano: ano ?? undefined })
      : caminho("sidra/rebanho", { animal, ano: ano ?? undefined });
  const lista = useBalcao<NormalizedResponse<IndicadorAgro>>(url);
  const anoRef = (lista.dados?.meta?.ano as number | undefined) ?? null;

  const dados = (lista.dados?.dados ?? []).filter((d) => d.valor != null);
  const max = dados[0]?.valor ?? 1; // o conector já devolve ordenado desc
  const total = dados.reduce((s, d) => s + (d.valor ?? 0), 0);
  const unidade = dados[0]?.unidade ?? null;
  const lider = dados[0];
  const oque = modo === "producao" ? PRODUTOS.find((p) => p[0] === produto)?.[1] : ANIMAIS.find((a) => a[0] === animal)?.[1];

  return (
    <div>
      <CadernoHeader
        numero="IX"
        kicker="IBGE + CONAB · agro"
        titulo="O agro, do campo à porteira"
        resumo="A safra que está no campo agora (estimativa mensal do IBGE e da CONAB), o trimestre da proteína (abate e leite com preço), o que o produtor recebe por kg em cada estado e os rankings anuais — por estado e por município."
      />

      <SafraAgora />

      <div className="regua-dupla my-10" />

      <AbateLeite />

      <div className="regua-dupla my-10" />

      <PrecoPorteira />

      <div className="regua-dupla my-10" />

      <div className="mb-4">
        <p className="kicker mb-1 text-accent-2">o retrato anual</p>
        <h2 className="font-display text-2xl font-semibold tracking-tight text-ink">
          Por estado
        </h2>
      </div>

      <div className="mb-6 flex flex-wrap items-center gap-4">
        <div className="flex gap-1 rounded-md border border-line bg-surface p-0.5">
          {(["producao", "rebanho"] as const).map((m) => (
            <button
              key={m}
              onClick={() => setModo(m)}
              aria-pressed={m === modo}
              className={`num rounded px-3 py-1 text-xs uppercase tracking-wider transition-colors ${
                m === modo ? "bg-accent/10 text-accent" : "text-muted hover:text-ink"
              }`}
            >
              {m === "producao" ? "lavoura" : "rebanho"}
            </button>
          ))}
        </div>

        {modo === "producao" ? (
          <>
            <Filtro rotulo="Cultura" valor={produto} aoMudar={setProduto} opcoes={PRODUTOS} />
            <Filtro rotulo="Medida" valor={variavel} aoMudar={setVariavel} opcoes={VARIAVEIS} />
          </>
        ) : (
          <Filtro rotulo="Rebanho" valor={animal} aoMudar={setAnimal} opcoes={ANIMAIS} />
        )}

        <div className="flex items-center gap-1">
          <button
            onClick={() => setAno(null)}
            aria-pressed={ano === null}
            className={`num rounded px-1.5 py-0.5 text-xs transition-colors ${
              ano === null ? "text-ink underline decoration-accent decoration-2 underline-offset-4" : "text-muted"
            }`}
          >
            {ano === null && anoRef ? `último (${anoRef})` : "último"}
          </button>
          {(anoRef ? anos(anoRef - 1, anoRef - 3) : []).map((a) => (
            <button
              key={a}
              onClick={() => setAno(a)}
              aria-pressed={a === ano}
              className={`num rounded px-1.5 py-0.5 text-xs transition-colors ${
                a === ano ? "text-ink underline decoration-accent decoration-2 underline-offset-4" : "text-muted"
              }`}
            >
              {a}
            </button>
          ))}
        </div>
      </div>

      <Card className="p-5 pt-6">
        <div className="flex items-start justify-between gap-3 pl-5">
          <div>
            <h2 className="font-display text-2xl leading-tight text-ink">
              {modo === "producao" ? "Produção de" : "Rebanho de"} {oque} · {ano ?? anoRef ?? "…"}
            </h2>
            <p className="num text-xs text-muted">
              {lista.carregando && !lista.dados ? "consultando…" : `${dados.length} estados com dado`}
            </p>
          </div>
          <Carimbo
            fonte="SIDRA"
            cache={lista.dados?.meta?.cache as string | undefined}
            ms={lista.ms}
            erro={!!lista.erro}
          />
        </div>

        <div className="my-5 pl-5">
          {lista.erro ? (
            <ErroBox erro={lista.erro} aoTentar={lista.recarregar} />
          ) : lista.carregando && !lista.dados ? (
            <Esqueleto linhas={6} />
          ) : dados.length === 0 ? (
            <Vazio>sem dado para essa combinação.</Vazio>
          ) : (
            <EmTransicao ativo={lista.carregando}>
              <div className="mb-6 flex flex-wrap gap-8">
                <div className="flex flex-col">
                  <span className="kicker mb-1">Total Brasil</span>
                  <span className="font-display text-4xl font-semibold leading-none tracking-tight text-accent-2 sm:text-5xl">
                    {compacto(total, unidade)}
                  </span>
                </div>
                {lider && (
                  <div className="flex flex-col">
                    <span className="kicker mb-1">Líder</span>
                    <span className="font-display text-4xl font-semibold leading-none tracking-tight text-ink sm:text-5xl">
                      {lider.localidade}
                    </span>
                    <span className="num mt-1 text-sm text-accent">{compacto(lider.valor ?? 0, unidade)}</span>
                  </div>
                )}
              </div>

              <ul className="flex flex-col gap-2.5">
                {dados.slice(0, 15).map((d, i) => (
                  <li key={d.localidade_id ?? d.localidade}>
                    <div className="mb-1 flex items-baseline justify-between gap-3">
                      <span className="truncate text-sm text-ink/85">{d.localidade}</span>
                      <span className={`num shrink-0 text-sm ${i === 0 ? "text-accent" : "text-ink"}`}>
                        {compacto(d.valor ?? 0, d.unidade)}
                      </span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-sm bg-surface-2">
                      <div
                        className={`h-full rounded-sm ${i === 0 ? "bg-accent" : "bg-accent-2/70"}`}
                        style={{ width: `${Math.max(((d.valor ?? 0) / max) * 100, 1.5)}%` }}
                      />
                    </div>
                  </li>
                ))}
              </ul>
            </EmTransicao>
          )}
        </div>
      </Card>

      <div className="regua-dupla my-10" />

      <MunicipiosCampeoes />

      <SeloFonte fonte={FONTE_SIDRA} />
    </div>
  );
}

function Filtro({
  rotulo,
  valor,
  aoMudar,
  opcoes,
}: {
  rotulo: string;
  valor: string;
  aoMudar: (v: string) => void;
  opcoes: [string, string][];
}) {
  return (
    <label className="num flex items-center gap-2 text-xs uppercase tracking-wider text-muted">
      {rotulo}
      <Seletor value={valor} onChange={(e) => aoMudar(e.target.value)}>
        {opcoes.map(([v, nome]) => (
          <option key={v} value={v}>
            {nome}
          </option>
        ))}
      </Seletor>
    </label>
  );
}
