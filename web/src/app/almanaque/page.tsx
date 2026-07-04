"use client";

import { useState } from "react";
import { CadernoHeader } from "@/components/Caderno";
import { Card } from "@/components/Card";
import { Carimbo } from "@/components/Carimbo";
import { SeloFonte } from "@/components/SeloFonte";
import { Seletor } from "@/components/Seletor";
import { Esqueleto, ErroBox, Vazio, EmTransicao } from "@/components/Estados";
import { useBalcao } from "@/hooks/useBalcao";
import { caminho, formataData, formataReaisCompacto } from "@/lib/api";
import type {
  FonteDado,
  FrequenciaNome,
  NomeNoEstado,
  NormalizedResponse,
  RankingNome,
  SorteioLoteria,
} from "@/lib/types";

const JOGOS: [string, string][] = [
  ["megasena", "Mega-Sena"],
  ["lotofacil", "Lotofácil"],
  ["quina", "Quina"],
  ["lotomania", "Lotomania"],
  ["duplasena", "Dupla Sena"],
  ["timemania", "Timemania"],
  ["diadesorte", "Dia de Sorte"],
  ["supersete", "Super Sete"],
  ["maismilionaria", "+Milionária"],
];

const NOMES_SUGERIDOS = ["Gabriel", "Maria", "Enzo", "Valentina", "José", "Larissa"];
const DECADAS = ["1930", "1940", "1950", "1960", "1970", "1980", "1990", "2000"];

function Dezenas({ lista, tom = "bg-accent" }: { lista: string[]; tom?: string }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {lista.map((d, i) => (
        <span
          key={i}
          className={`num flex h-9 w-9 items-center justify-center rounded-full ${tom} text-sm font-semibold text-white`}
        >
          {d}
        </span>
      ))}
    </div>
  );
}

function Sorteio({ jogo }: { jogo: string }) {
  const r = useBalcao<NormalizedResponse<SorteioLoteria>>(caminho("loterias/resultado", { jogo }));
  const s = r.dados?.dados?.[0];

  if (r.erro) return <ErroBox erro={r.erro} aoTentar={r.recarregar} />;
  if (r.carregando && !r.dados) return <Esqueleto linhas={4} />;
  if (!s) return <Vazio>a CAIXA não respondeu o resultado agora.</Vazio>;

  return (
    <EmTransicao ativo={r.carregando}>
      <Card className="p-5">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <span className="kicker">
            concurso {s.concurso}
            {s.data ? ` · ${formataData(s.data)}` : ""}
          </span>
          {s.acumulado && (
            <span className="num rounded-full bg-ocre/15 px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wider text-ocre">
              acumulou!
            </span>
          )}
        </div>
        <Dezenas lista={s.dezenas} />
        {s.dezenas_2 && (
          <div className="mt-2">
            <p className="kicker mb-1.5">2º sorteio</p>
            <Dezenas lista={s.dezenas_2} tom="bg-accent-2" />
          </div>
        )}
        {s.extra && <p className="num mt-2 text-xs text-muted">extra: {s.extra}</p>}
        <ul className="mt-4 flex flex-col divide-y divide-line/60">
          {s.premios.map((p, i) => (
            <li key={i} className="flex flex-wrap items-baseline justify-between gap-x-4 py-1.5">
              <span className="text-sm text-ink/85">{p.faixa}</span>
              <span className="num text-xs text-muted">
                {p.ganhadores === 0
                  ? "ninguém acertou"
                  : `${p.ganhadores.toLocaleString("pt-BR")} ganhador${p.ganhadores > 1 ? "es" : ""}`}
              </span>
              <span className="num text-sm text-ink">
                {Number(p.valor) > 0 ? formataReaisCompacto(p.valor) : "—"}
              </span>
            </li>
          ))}
        </ul>
        {s.cidades_ganhadoras.length > 0 && (
          <p className="num mt-2 text-xs text-muted">
            a sorte caiu em:{" "}
            {s.cidades_ganhadoras
              .map((c) => `${c.municipio ?? "?"}${c.uf ? `-${c.uf}` : ""}`)
              .join(", ")}
          </p>
        )}
        {s.estimativa_proximo && Number(s.estimativa_proximo) > 0 && (
          <p className="mt-4 border-t border-line pt-3 font-editorial text-sm text-ink/80">
            próximo sorteio{s.data_proximo ? ` em ${formataData(s.data_proximo)}` : ""}:{" "}
            <span className="num font-semibold text-ok">
              {formataReaisCompacto(s.estimativa_proximo)}
            </span>{" "}
            estimados
          </p>
        )}
      </Card>
    </EmTransicao>
  );
}

function MeuNome({ nome }: { nome: string }) {
  const porDecada = useBalcao<NormalizedResponse<FrequenciaNome>>(
    caminho("ibge/nomes", { nome }),
  );
  const porUf = useBalcao<NormalizedResponse<NomeNoEstado>>(
    caminho("ibge/nomes", { nome, por: "uf" }),
  );
  const decadas = porDecada.dados?.dados ?? [];
  const estados = porUf.dados?.dados ?? [];
  const total = porDecada.dados?.meta?.total_pessoas as number | undefined;
  const aviso = porDecada.dados?.meta?.aviso as string | undefined;

  if (porDecada.erro) return <ErroBox erro={porDecada.erro} aoTentar={porDecada.recarregar} />;
  if (porDecada.carregando && !porDecada.dados) return <Esqueleto linhas={4} />;
  if (aviso || !decadas.length) return <Vazio>{aviso ?? "nada encontrado."}</Vazio>;

  const maior = Math.max(...decadas.map((d) => d.frequencia));
  const pico = decadas.find((d) => d.frequencia === maior);

  return (
    <EmTransicao ativo={porDecada.carregando}>
      <Card className="p-5">
        <p className="font-editorial text-sm leading-relaxed text-ink/80">
          <span className="font-semibold text-ink">{decadas[0].nome}</span>:{" "}
          <span className="num font-semibold text-ink">{total?.toLocaleString("pt-BR")}</span>{" "}
          brasileiros no Censo 2010
          {pico && (
            <>
              {" "}
              — o auge foi {pico.decada.startsWith("até") ? pico.decada : `nos anos ${pico.decada}`}
            </>
          )}
          .
        </p>
        <div className="mt-4 flex h-24 items-end gap-1">
          {decadas.map((d) => (
            <div key={d.decada} className="flex min-w-0 flex-1 flex-col items-center gap-1">
              <div
                title={`${d.decada}: ${d.frequencia.toLocaleString("pt-BR")}`}
                className="w-full rounded-t-sm bg-accent-2/60 transition-colors hover:bg-accent-2"
                style={{ height: `${Math.max(3, (d.frequencia / maior) * 100)}%` }}
              />
              <span className="num truncate text-[0.6rem] text-muted">{d.decada}</span>
            </div>
          ))}
        </div>
        {estados.length > 0 && (
          <p className="num mt-4 border-t border-line pt-3 text-xs text-muted">
            onde é mais comum (por 100 mil hab):{" "}
            <span className="text-ink">
              {estados
                .slice(0, 5)
                .map((e) => `${e.uf} (${e.por_100k?.toLocaleString("pt-BR")})`)
                .join(" · ")}
            </span>
          </p>
        )}
      </Card>
    </EmTransicao>
  );
}

function RankingDeNomes() {
  const [decada, setDecada] = useState("2000");
  const [sexo, setSexo] = useState("");
  const r = useBalcao<NormalizedResponse<RankingNome>>(
    caminho("ibge/nomes/ranking", { decada, sexo: sexo || undefined, limit: 10 }),
  );
  const itens = r.dados?.dados ?? [];

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Seletor value={decada} onChange={(e) => setDecada(e.target.value)} aria-label="década">
          {DECADAS.map((d) => (
            <option key={d} value={d}>
              anos {d}
            </option>
          ))}
        </Seletor>
        <div className="inline-flex gap-0.5 rounded-md border border-line p-0.5">
          {[
            ["", "todos"],
            ["f", "meninas"],
            ["m", "meninos"],
          ].map(([v, label]) => (
            <button
              key={v}
              onClick={() => setSexo(v)}
              aria-pressed={sexo === v}
              className={`num rounded px-3 py-1 text-xs uppercase tracking-wider transition-colors ${
                sexo === v ? "bg-accent/15 font-semibold text-accent" : "text-muted hover:text-ink"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
      {r.erro ? (
        <ErroBox erro={r.erro} aoTentar={r.recarregar} />
      ) : r.carregando && !r.dados ? (
        <Esqueleto linhas={5} />
      ) : itens.length ? (
        <EmTransicao ativo={r.carregando}>
          <Card className="p-5">
            <ol className="grid gap-x-8 gap-y-1.5 sm:grid-cols-2">
              {itens.map((i) => (
                <li key={i.posicao} className="flex items-baseline justify-between gap-3">
                  <span className="text-sm text-ink">
                    <span className="num mr-2 inline-block w-6 text-right text-xs text-muted">
                      {i.posicao}º
                    </span>
                    {i.nome}
                  </span>
                  <span className="num text-xs text-muted">
                    {i.frequencia.toLocaleString("pt-BR")}
                  </span>
                </li>
              ))}
            </ol>
          </Card>
        </EmTransicao>
      ) : (
        <Vazio>sem ranking pra esse recorte.</Vazio>
      )}
    </div>
  );
}

export default function CadernoAlmanaque() {
  const [jogo, setJogo] = useState("megasena");
  const [texto, setTexto] = useState("");
  const [consultado, setConsultado] = useState("");

  const r = useBalcao<NormalizedResponse<SorteioLoteria>>(
    caminho("loterias/resultado", { jogo }),
  );
  const fonteLoterias = r.dados?.meta?.fonte as FonteDado | undefined;
  const s = r.dados?.dados?.[0];

  return (
    <div>
      <CadernoHeader
        numero="XXXIII"
        kicker="Loterias CAIXA · IBGE"
        titulo="Almanaque"
        resumo="A parte do jornal que todo mundo abre primeiro: deu quanto na Mega? E o dado que ninguém sabia que queria: quantos brasileiros têm o seu nome — e quando ele esteve na moda."
        referencia={s ? `concurso ${s.concurso}${s.data ? ` · ${formataData(s.data)}` : ""}` : undefined}
      />

      <section className="mb-10">
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <h2 className="font-display text-lg font-semibold text-ink">Deu quanto?</h2>
          <Seletor value={jogo} onChange={(e) => setJogo(e.target.value)} aria-label="jogo">
            {JOGOS.map(([v, label]) => (
              <option key={v} value={v}>
                {label}
              </option>
            ))}
          </Seletor>
          <Carimbo fonte="CAIXA" cache={r.dados?.meta?.cache as string | undefined} ms={r.ms} erro={!!r.erro} />
        </div>
        <Sorteio jogo={jogo} />
      </section>

      <section className="mb-10">
        <h2 className="mb-1 font-display text-lg font-semibold text-ink">Seu nome no Brasil</h2>
        <p className="mb-4 max-w-2xl font-editorial text-sm leading-relaxed text-ink/75">
          O Censo 2010 contou os primeiros nomes de todo o país. Digite o seu e veja a história
          dele, década a década.
        </p>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            setConsultado(texto.trim());
          }}
          className="mb-3 flex flex-wrap gap-2"
        >
          <input
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            placeholder="um primeiro nome"
            aria-label="primeiro nome"
            className="num min-h-9 w-64 max-w-full rounded-md border border-line bg-surface px-3 text-sm text-ink placeholder:text-muted focus:border-accent focus:outline-none"
          />
          <button
            type="submit"
            className="num inline-flex min-h-9 items-center rounded-md border border-line px-3.5 text-xs uppercase tracking-wider text-ink transition-colors hover:bg-surface-2"
          >
            procurar
          </button>
        </form>
        <div className="mb-5 flex flex-wrap items-center gap-2">
          <span className="kicker">experimente:</span>
          {NOMES_SUGERIDOS.map((n) => (
            <button
              key={n}
              onClick={() => {
                setTexto(n);
                setConsultado(n);
              }}
              className="num rounded-full border border-line px-3 py-1 text-xs text-ink transition-colors hover:border-accent hover:text-accent"
            >
              {n}
            </button>
          ))}
        </div>
        {consultado ? <MeuNome nome={consultado} /> : <Vazio>digite um nome — ou toque numa sugestão.</Vazio>}
      </section>

      <section>
        <h2 className="mb-1 font-display text-lg font-semibold text-ink">Os nomes do Brasil</h2>
        <p className="mb-4 max-w-2xl font-editorial text-sm leading-relaxed text-ink/75">
          Os dez mais registrados em cada década — dá pra ver a moda mudando.
        </p>
        <RankingDeNomes />
      </section>

      <SeloFonte fonte={fonteLoterias} />
    </div>
  );
}
