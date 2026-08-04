"use client";

import { useEffect, useRef, useState } from "react";
import { CadernoHeader } from "@/components/Caderno";
import { Card } from "@/components/Card";
import { BadgeAoVivo } from "@/components/Frescor";
import { SeloFonte } from "@/components/SeloFonte";
import { Esqueleto, ErroBox } from "@/components/Estados";
import { useBalcao } from "@/hooks/useBalcao";
import { useTicker } from "@/hooks/useTicker";
import { caminho } from "@/lib/api";
import type { Acao, Cotacao, NormalizedResponse } from "@/lib/types";

// o gateway serve as cotações pela AwesomeAPI e, quando ela recusa, por
// fontes abertas. A tela mostra o selo de quem realmente serviu o número.
const FONTES_CAMBIO: Record<string, { nome: string; url: string; nota: string }> = {
  awesomeapi: {
    nome: "AwesomeAPI, cotações em tempo real",
    url: "https://docs.awesomeapi.com.br/",
    nota: "Câmbio, ouro e cripto atualizados a cada poucos segundos. O dólar oficial de referência (PTAX) é o do Banco Central; este aqui é o mercado se mexendo ao vivo.",
  },
  frankfurter: {
    nome: "Frankfurter, taxa de referência do Banco Central Europeu",
    url: "https://frankfurter.dev/",
    nota: "O BCE publica uma taxa de referência por dia útil, no fim da tarde. É câmbio de verdade e conferível, mas não é o mercado de segundo a segundo: por isso estas moedas não levam selo de ao vivo.",
  },
  binance: {
    nome: "Binance, preço à vista das criptomoedas",
    url: "https://www.binance.com/",
    nota: "Preço da última negociação do par em real, com a variação das últimas 24 horas. Mercado aberto todo dia, o tempo todo.",
  },
  "gold-api": {
    nome: "gold-api, preço do ouro",
    url: "https://gold-api.com/",
    nota: "Cotação da onça troy em dólar, convertida para real pelo câmbio do dia. Ouro é negociado em dólar no mundo inteiro.",
  },
};

const FONTE_BOLSA = {
  nome: "brapi, dados da B3",
  url: "https://brapi.dev/",
  nota: "Ibovespa e ações da bolsa brasileira. No plano gratuito os preços chegam com ~15 minutos de atraso, e é por isso que a bolsa não leva selo de ao vivo.",
};

const PARES = "USD-BRL,EUR-BRL,GBP-BRL,XAU-BRL,BTC-BRL,ETH-BRL,SOL-BRL";
const INTERVALO = 20000; // 20s

// o telão em seções: moedas, ouro e cripto (a ordem dentro de cada uma importa)
const GRUPOS: { titulo: string; nota?: string; pares: string[] }[] = [
  { titulo: "Moedas", pares: ["USD/BRL", "EUR/BRL", "GBP/BRL"] },
  { titulo: "Ouro", nota: "cotação da onça troy (31,1 g)", pares: ["XAU/BRL"] },
  { titulo: "Cripto", pares: ["BTC/BRL", "ETH/BRL", "SOL/BRL"] },
];

// rótulo amigável quando a sigla do par não se explica sozinha
const APELIDOS: Record<string, string> = { "XAU/BRL": "OURO" };

// a bolsa vem por outra fonte (b3), com ~15 min de atraso no plano gratuito
const TICKERS_B3 = "ibov,PETR4,VALE3,ITUB4";

function formataPreco(v: number): string {
  if (v >= 1000) return v.toLocaleString("pt-BR", { maximumFractionDigits: 0 });
  return v.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 4 });
}

// a fonte de tempo real carimba hora; a taxa diária do BCE só tem data. Mostra
// o que existir, sem inventar precisão que o dado não tem.
function quandoDe(ts: string | null): string {
  const hora = ts?.match(/\d{2}:\d{2}:\d{2}/);
  if (hora) return hora[0];
  const dia = ts?.match(/(\d{4})-(\d{2})-(\d{2})/);
  return dia ? `${dia[3]}/${dia[2]}` : "sem data";
}

function TickerCotacao({ c }: { c: Cotacao }) {
  const alvo = Number(c.compra);
  const valor = useTicker(alvo);
  const anterior = useRef(alvo);
  const [dir, setDir] = useState<"sobe" | "desce" | null>(null);

  // quando o valor muda entre dois polls, pisca verde (subiu) ou vermelho (caiu)
  useEffect(() => {
    if (alvo > anterior.current) setDir("sobe");
    else if (alvo < anterior.current) setDir("desce");
    anterior.current = alvo;
    const id = setTimeout(() => setDir(null), 1000);
    return () => clearTimeout(id);
  }, [alvo]);

  // sem variação conhecida (o ouro vem só com o preço), a seta fica de fora:
  // "▲ 0,00%" pareceria um dia parado, e não é isso que a fonte disse
  const variacao = c.variacao_pct;
  const positiva = (variacao ?? 0) >= 0;
  const corValor =
    dir === "sobe" ? "text-emerald-500" : dir === "desce" ? "text-rose-500" : "text-ink";

  return (
    <Card className="p-5">
      <div className="flex items-baseline justify-between">
        <span className="num text-sm font-semibold uppercase tracking-wider text-ink">
          {APELIDOS[c.par] ?? c.par}
        </span>
        {variacao == null ? (
          <span className="num text-xs text-muted">sem variação</span>
        ) : (
          <span className={`num text-xs ${positiva ? "text-emerald-500" : "text-rose-500"}`}>
            {positiva ? "▲" : "▼"} {Math.abs(variacao).toFixed(2)}%
          </span>
        )}
      </div>
      <p
        className={`num mt-2 font-display text-3xl sm:text-4xl font-semibold tracking-tight transition-colors duration-500 ${corValor}`}
      >
        R$ {formataPreco(valor)}
      </p>
      <p className="mt-1.5 truncate text-xs text-muted" title={c.nome ?? ""}>
        {c.nome} · {quandoDe(c.atualizado)}
        {!c.ao_vivo && <span className="ml-1">· taxa do dia</span>}
      </p>
    </Card>
  );
}

function CardAcao({ a }: { a: Acao }) {
  const indice = a.moeda == null;
  const preco = Number(a.preco);
  const variacao = a.variacao_pct ?? 0;
  const positiva = variacao >= 0;
  return (
    <Card className="p-5">
      <div className="flex items-baseline justify-between">
        <span className="num text-sm font-semibold uppercase tracking-wider text-ink">{a.ticker}</span>
        <span className={`num text-xs ${positiva ? "text-emerald-500" : "text-rose-500"}`}>
          {positiva ? "▲" : "▼"} {Math.abs(variacao).toFixed(2)}%
        </span>
      </div>
      <p className="num mt-2 font-display text-3xl sm:text-4xl font-semibold tracking-tight text-ink">
        {indice
          ? preco.toLocaleString("pt-BR", { maximumFractionDigits: 0 })
          : `R$ ${preco.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
        {indice && <span className="ml-1.5 align-baseline text-base text-muted">pts</span>}
      </p>
      <p className="mt-1.5 truncate text-xs text-muted" title={a.nome ?? ""}>
        {a.nome}
      </p>
    </Card>
  );
}

export default function CadernoPulso() {
  const cot = useBalcao<NormalizedResponse<Cotacao>>(caminho(`cotacoes/last/${PARES}`));
  const bolsa = useBalcao<NormalizedResponse<Acao>>(caminho(`b3/acoes/${TICKERS_B3}`));
  const cotacoes = cot.dados?.dados ?? [];
  const acoes = bolsa.dados?.dados ?? [];
  const { recarregar } = cot;
  const recarregarBolsa = bolsa.recarregar;

  // o selo segue o dado: só entra a fonte que de fato serviu alguma cotação
  const origens = [...new Set(cotacoes.map((c) => c.origem))];
  const temAoVivo = cotacoes.some((c) => c.ao_vivo);
  const temTaxaDoDia = cotacoes.some((c) => !c.ao_vivo);

  // transparência do ao-vivo: marca a hora de cada resposta nova pro selo
  const [atualizadoEm, setAtualizadoEm] = useState<number | null>(null);
  useEffect(() => {
    if (cot.dados) setAtualizadoEm(Date.now());
  }, [cot.dados]);

  // polling: refaz a cada 20s pra o número mudar sozinho quando o mercado mexe.
  // a bolsa entra no mesmo ciclo, o cache do gateway segura o upstream
  useEffect(() => {
    const id = setInterval(() => {
      recarregar();
      recarregarBolsa();
    }, INTERVALO);
    return () => clearInterval(id);
  }, [recarregar, recarregarBolsa]);

  return (
    <div>
      <CadernoHeader
        numero="XII"
        kicker="mercado · câmbio, ouro e cripto"
        titulo="Pulso do Brasil"
        resumo="Câmbio, ouro e cripto quase em tempo real, pelo preço de mercado. A página se atualiza sozinha a cada 20 segundos, quando o mercado mexe, o número desliza pro novo valor. Dado vivo, não a foto de ontem."
      />

      <div className="mb-5 flex flex-wrap items-center gap-3">
        {temAoVivo && <BadgeAoVivo atualizadoEm={atualizadoEm} />}
        <span className="num text-xs uppercase tracking-wider text-muted">a cada 20s, sozinho</span>
      </div>

      {/* quando a fonte de tempo real não atende, o caderno continua de pé por
          fontes abertas. Dizer isso na cara do leitor é parte do trato. */}
      {temTaxaDoDia && (
        <p className="mb-5 rounded-lg border border-line bg-surface-2/40 p-4 font-editorial text-sm italic text-ink/70">
          A fonte de tempo real não está atendendo agora, então o câmbio abaixo é a taxa de
          referência que o Banco Central Europeu publica uma vez por dia útil. Ouro e cripto seguem
          com preço de mercado. Cada quadro diz de onde veio o número.
        </p>
      )}

      {cot.erro ? (
        <ErroBox erro={cot.erro} aoTentar={recarregar} />
      ) : !cotacoes.length ? (
        <Esqueleto linhas={4} />
      ) : (
        <div className="flex flex-col gap-7">
          {GRUPOS.map((g) => {
            const doGrupo = g.pares
              .map((par) => cotacoes.find((c) => c.par === par))
              .filter((c): c is Cotacao => Boolean(c));
            if (!doGrupo.length) return null;
            return (
              <section key={g.titulo}>
                <p className="kicker mb-3">
                  {g.titulo}
                  {g.nota && <span className="ml-2 normal-case tracking-normal text-muted">· {g.nota}</span>}
                </p>
                <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
                  {doGrupo.map((c) => (
                    <TickerCotacao key={c.par} c={c} />
                  ))}
                </div>
              </section>
            );
          })}

          {acoes.length > 0 && (
            <section>
              <p className="kicker mb-3">
                Bolsa
                <span className="ml-2 normal-case tracking-normal text-muted">
                  · B3, com ~15 min de atraso
                </span>
              </p>
              <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
                {acoes.map((a) => (
                  <CardAcao key={a.ticker} a={a} />
                ))}
              </div>
            </section>
          )}
        </div>
      )}

      <p className="mt-7 border-t border-line pt-3 font-editorial text-sm italic text-muted">
        Cotações de mercado (preço de referência, não o câmbio oficial). O dólar oficial do Banco
        Central (PTAX) fica no caderno do Banco Central, e ele muda só algumas vezes ao dia.
      </p>

      {origens.map((origem) => (
        <SeloFonte key={origem} fonte={FONTES_CAMBIO[origem]} />
      ))}
      {acoes.length > 0 && <SeloFonte fonte={FONTE_BOLSA} />}
    </div>
  );
}
