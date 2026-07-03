"use client";

import { useState } from "react";
import { CadernoHeader } from "@/components/Caderno";
import { Card } from "@/components/Card";
import { Carimbo } from "@/components/Carimbo";
import { BadgeFrescor } from "@/components/Frescor";
import { SeloFonte } from "@/components/SeloFonte";
import { Termo } from "@/components/Termo";
import { Esqueleto, ErroBox, EmTransicao } from "@/components/Estados";
import { useBalcao } from "@/hooks/useBalcao";
import { caminho, formataData } from "@/lib/api";
import { ANO_ATUAL, anos } from "@/lib/datas";
import type {
  ExpectativaMercado,
  IndicadorEconomico,
  NormalizedResponse,
} from "@/lib/types";

const FONTE_BACEN = {
  nome: "Banco Central — Sistema Gerenciador de Séries (SGS)",
  url: "https://www3.bcb.gov.br/sgspub/",
  nota: "IPCA, INPC e IGP-M são os índices oficiais de inflação; Selic, CDI e poupança medem o preço do dinheiro. O Balcão entrega o valor mais recente que o Banco Central publicou, já em ISO 8601.",
};

const FONTE_FOCUS = {
  nome: "Banco Central — Boletim Focus",
  url: "https://www.bcb.gov.br/publicacoes/focus",
  nota: "Projeção mediana de mais de cem instituições financeiras, coletada e divulgada toda semana pelo Banco Central. É expectativa de mercado, não previsão oficial.",
};

// o horizonte do Focus acompanha o calendário: este ano e os dois seguintes
const ANOS = anos(ANO_ATUAL, ANO_ATUAL + 2);

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
        className={`num tabular-nums pl-4 text-3xl font-semibold leading-none tracking-tight ${
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
      <p className="num tabular-nums pl-4 text-3xl font-semibold leading-none tracking-tight text-accent-2">
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

  return (
    <div>
      <CadernoHeader
        numero="XIV"
        kicker="Banco Central"
        titulo="Custo de vida"
        resumo="A inflação que já corroeu o seu bolso — IPCA, IGP-M (o do aluguel), INPC — e o que os analistas do Boletim Focus esperam pra frente. Dois olhares do Banco Central: o retrospecto e a expectativa."
      />

      <div className="mb-5 flex flex-wrap items-center gap-3">
        <BadgeFrescor rotulo="índices mensais" detalhe="Selic, CDI e dólar diários · Focus toda semana" />
      </div>

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
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
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
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
                {expectativas.map((e) => (
                  <CartaoFocus key={e.indicador} e={e} />
                ))}
              </div>
            </EmTransicao>
          ))}

        <SeloFonte fonte={FONTE_FOCUS} />
      </section>
    </div>
  );
}
