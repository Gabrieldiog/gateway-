"use client";

import { useState } from "react";
import { CadernoHeader } from "@/components/Caderno";
import { Card } from "@/components/Card";
import { Carimbo } from "@/components/Carimbo";
import { SeloFonte } from "@/components/SeloFonte";
import { Termo } from "@/components/Termo";
import { Esqueleto, ErroBox, Vazio, EmTransicao } from "@/components/Estados";
import { useBalcao } from "@/hooks/useBalcao";
import { caminho, formataData } from "@/lib/api";
import { ANO_ATUAL, anos } from "@/lib/datas";
import type {
  ExpectativaMercado,
  FonteDado,
  IndicadorEconomico,
  NormalizedResponse,
  TaxaJurosBanco,
} from "@/lib/types";

const FONTE_BACEN = {
  nome: "Banco Central, Sistema Gerenciador de Séries (SGS)",
  url: "https://www3.bcb.gov.br/sgspub/",
  nota: "IPCA, INPC e IGP-M são os índices oficiais de inflação; Selic, CDI e poupança medem o preço do dinheiro. O Balcão entrega o valor mais recente que o Banco Central publicou, já em ISO 8601.",
};

const FONTE_FOCUS = {
  nome: "Banco Central, Boletim Focus",
  url: "https://www.bcb.gov.br/publicacoes/focus",
  nota: "Projeção mediana de mais de cem instituições financeiras, coletada e divulgada toda semana pelo Banco Central. É expectativa de mercado, não previsão oficial.",
};

// o horizonte do Focus acompanha o calendário: este ano e os dois seguintes
const ANOS = anos(ANO_ATUAL, ANO_ATUAL + 2);

// o primeiro valor vai como filtro de modalidade na API do BCB
const MODALIDADES_JUROS = [
  ["rotativo", "Cartão rotativo"],
  ["Cheque especial", "Cheque especial"],
  ["consignado INSS", "Consignado INSS"],
  ["Aquisição de veículos", "Financiamento de veículo"],
  ["não consignado", "Crédito pessoal"],
] as const;

// verde no banco barato, vermelho no caro; interpola pela posição no ranking
function corJuros(frac: number): string {
  const de = [16, 185, 129]; // emerald
  const ate = [225, 29, 72]; // rose
  const [r, g, b] = de.map((v, i) => Math.round(v + (ate[i] - v) * frac));
  return `rgb(${r}, ${g}, ${b})`;
}

function pctAno(taxa: number | null): string {
  if (taxa == null) return "sem dado";
  return `${taxa.toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}% a.a.`;
}

function JurosBancos() {
  const [modalidade, setModalidade] = useState<string>(MODALIDADES_JUROS[0][0]);

  const r = useBalcao<NormalizedResponse<TaxaJurosBanco>>(
    caminho("bacen/juros-bancos", { modalidade, limit: 12 }),
  );
  const linhas = r.dados?.dados ?? [];
  const max = linhas.reduce((m, l) => Math.max(m, l.taxa_ano ?? 0), 0) || 1;
  const janelaDe = r.dados?.meta?.janela_de as string | undefined;
  const janelaAte = r.dados?.meta?.janela_ate as string | undefined;
  const fonte = r.dados?.meta?.fonte as FonteDado | undefined;

  return (
    <section>
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="kicker mb-1 text-accent">juros banco a banco</p>
          <h2 className="font-display text-2xl font-semibold tracking-tight text-ink">
            Quanto o seu banco cobra
          </h2>
        </div>
        <Carimbo
          fonte="BACEN"
          cache={r.dados?.meta?.cache as string | undefined}
          ms={r.ms}
          erro={!!r.erro}
        />
      </div>

      <div className="mb-5 flex flex-wrap items-center gap-2">
        {MODALIDADES_JUROS.map(([v, label]) => (
          <button
            key={v}
            onClick={() => setModalidade(v)}
            aria-pressed={v === modalidade}
            className={`num rounded-full border px-3 py-1 text-xs uppercase tracking-wider transition-colors ${
              v === modalidade
                ? "border-accent bg-accent text-surface"
                : "border-line text-muted hover:border-accent hover:text-accent"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {r.erro ? (
        <ErroBox erro={r.erro} aoTentar={r.recarregar} />
      ) : r.carregando && !r.dados ? (
        <Esqueleto linhas={8} />
      ) : !linhas.length ? (
        <Vazio>o Banco Central não publicou taxas pra essa modalidade na última janela.</Vazio>
      ) : (
        <EmTransicao ativo={r.carregando}>
          <Card className="p-5 sm:p-6">
            <ol className="flex flex-col gap-3">
              {linhas.map((l, i) => {
                const caro = i === linhas.length - 1 && linhas.length > 1;
                return (
                  <li key={`${l.posicao}-${l.instituicao}`} className="flex items-center gap-3">
                    <span className="num w-6 shrink-0 text-right text-sm text-muted">
                      {l.posicao}
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="mb-1 flex items-baseline justify-between gap-3">
                        <span
                          className={`truncate text-sm ${caro ? "font-semibold text-erro" : "text-ink/90"}`}
                          title={l.instituicao}
                        >
                          {l.instituicao}
                        </span>
                        <span className={`num shrink-0 text-sm ${caro ? "font-semibold text-erro" : "text-ink"}`}>
                          {pctAno(l.taxa_ano)}
                        </span>
                      </div>
                      <div className="h-2 overflow-hidden rounded-sm bg-surface-2">
                        <div
                          className="h-full rounded-sm transition-all duration-500"
                          style={{
                            width: `${Math.max(((l.taxa_ano ?? 0) / max) * 100, 1.5)}%`,
                            background: corJuros(linhas.length > 1 ? i / (linhas.length - 1) : 0),
                          }}
                        />
                      </div>
                    </div>
                  </li>
                );
              })}
            </ol>
            {janelaDe && janelaAte && (
              <p className="mt-5 border-t border-line pt-3 font-editorial text-sm italic text-muted">
                Taxas médias efetivamente cobradas na janela de {formataData(janelaDe)} a{" "}
                {formataData(janelaAte)}, apuradas pelo Banco Central. O ranking muda a cada
                semana.
              </p>
            )}
          </Card>
        </EmTransicao>
      )}

      <SeloFonte fonte={fonte} />
    </section>
  );
}

// mostra o valor de um indicador do bolso: % com o sinal, R$ com o cifrão
function textoValor(valor: number, unidade: string): string {
  if (unidade.startsWith("R$")) {
    return `R$ ${valor.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 4 })}`;
  }
  return `${valor.toLocaleString("pt-BR", { maximumFractionDigits: 2 })}%`;
}

function CartaoHoje({ ind, destaque }: { ind: IndicadorEconomico; destaque?: boolean }) {
  const valor = Number(ind.valor);
  return (
    <Card className={`p-4 pt-5 ${destaque ? "border-accent/45" : ""}`}>
      <p className="kicker mb-2 pl-4">
        <Termo t={ind.chave}>{ind.nome}</Termo>
      </p>
      <p
        className={`num tabular-nums pl-4 text-2xl sm:text-3xl font-semibold leading-none tracking-tight ${
          destaque ? "text-accent" : "text-ink"
        }`}
      >
        {textoValor(valor, ind.unidade)}
      </p>
      <p className="num mt-2 pl-4 text-[0.7rem] uppercase tracking-wider text-muted">
        {ind.unidade} · {formataData(ind.data)}
      </p>
    </Card>
  );
}

function CartaoFocus({ e }: { e: ExpectativaMercado }) {
  const pct = !e.unidade.startsWith("R$");
  const med = e.mediana ?? 0;
  const texto = pct
    ? `${med.toLocaleString("pt-BR", { maximumFractionDigits: 2 })}%`
    : `R$ ${med.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  const fmt = (n: number) => n.toLocaleString("pt-BR", { maximumFractionDigits: 2 });
  const faixa =
    e.minimo != null && e.maximo != null ? `${fmt(e.minimo)} – ${fmt(e.maximo)}` : null;
  return (
    <Card className="p-4 pt-5">
      <p className="kicker mb-2 pl-4">{e.indicador}</p>
      <p className="num tabular-nums pl-4 text-2xl sm:text-3xl font-semibold leading-none tracking-tight text-accent-2">
        {texto}
      </p>
      <div className="mt-2 space-y-0.5 pl-4">
        {faixa && <p className="num text-[0.7rem] text-muted">mín–máx {faixa}</p>}
        {e.respondentes != null && (
          <p className="num text-[0.7rem] uppercase tracking-wider text-muted">
            {e.respondentes} analistas
          </p>
        )}
      </div>
    </Card>
  );
}

export default function CadernoCustoDeVida() {
  const [ano, setAno] = useState(ANO_ATUAL);

  const hoje = useBalcao<NormalizedResponse<IndicadorEconomico>>(caminho("bacen/inflacao"));
  const focus = useBalcao<NormalizedResponse<ExpectativaMercado>>(
    caminho("focus/painel", { ano }),
  );

  const indicadores = hoje.dados?.dados ?? [];
  const expectativas = focus.dados?.dados ?? [];
  const coleta = expectativas[0]?.data ?? null;
  const ptax = indicadores.find((i) => i.chave === "dolar")?.data;

  return (
    <div>
      <CadernoHeader
        numero="XIV"
        kicker="Banco Central"
        titulo="Custo de vida"
        resumo="A inflação que já corroeu o seu bolso: IPCA, IGP-M (o do aluguel) e INPC. E o que os analistas do Boletim Focus esperam pra frente. Dois olhares do Banco Central: o retrospecto e a expectativa."
        referencia={ptax ? `dólar (PTAX) de ${formataData(ptax)}` : undefined}
      />

      <section>
        <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="kicker mb-1 text-accent">agora</p>
            <h2 className="font-display text-2xl font-semibold tracking-tight text-ink">
              O Brasil hoje
            </h2>
          </div>
          <Carimbo
            fonte="BACEN"
            cache={hoje.dados?.meta?.cache as string | undefined}
            ms={hoje.ms}
          />
        </div>

        {hoje.erro && <ErroBox erro={hoje.erro} aoTentar={hoje.recarregar} />}

        {!hoje.erro &&
          (hoje.carregando && !hoje.dados ? (
            <Esqueleto linhas={4} />
          ) : (
            <div className="grid grid-cols-1 gap-3 min-[380px]:grid-cols-2 sm:grid-cols-3 lg:grid-cols-4">
              {indicadores.map((ind) => (
                <CartaoHoje
                  key={ind.chave}
                  ind={ind}
                  destaque={ind.chave === "ipca12m" || ind.chave === "dolar"}
                />
              ))}
            </div>
          ))}

        <SeloFonte fonte={FONTE_BACEN} />
      </section>

      <div className="regua-dupla my-10" />

      <section>
        <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="kicker mb-1 text-accent-2">expectativa</p>
            <h2 className="font-display text-2xl font-semibold tracking-tight text-ink">
              O que o mercado espera
            </h2>
            <p className="mt-1 max-w-[52ch] font-editorial text-sm text-ink/70">
              Projeção mediana do <Termo t="focus">Boletim Focus</Termo> para {ano}
              {coleta && (
                <>
                  {" "}
                  · coleta de <span className="num">{formataData(coleta)}</span>
                </>
              )}
              .
            </p>
          </div>
          <div className="flex items-center gap-2">
            {ANOS.map((a) => (
              <button
                key={a}
                onClick={() => setAno(a)}
                aria-pressed={a === ano}
                className={`num rounded-full border px-3 py-1 text-xs uppercase tracking-wider transition-colors ${
                  a === ano
                    ? "border-accent-2 bg-accent-2 text-surface"
                    : "border-line text-muted hover:border-accent-2 hover:text-accent-2"
                }`}
              >
                {a}
              </button>
            ))}
          </div>
        </div>

        {focus.erro && <ErroBox erro={focus.erro} aoTentar={focus.recarregar} />}

        {!focus.erro &&
          (focus.carregando && !focus.dados ? (
            <Esqueleto linhas={3} />
          ) : (
            <EmTransicao ativo={focus.carregando}>
              <div className="grid grid-cols-1 gap-3 min-[380px]:grid-cols-2 sm:grid-cols-3 lg:grid-cols-5">
                {expectativas.map((e) => (
                  <CartaoFocus key={e.indicador} e={e} />
                ))}
              </div>
            </EmTransicao>
          ))}

        <SeloFonte fonte={FONTE_FOCUS} />
      </section>

      <div className="regua-dupla my-10" />

      <JurosBancos />
    </div>
  );
}
