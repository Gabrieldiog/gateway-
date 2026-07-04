"use client";

import { useState } from "react";
import Link from "next/link";
import { CadernoHeader } from "@/components/Caderno";
import { Card } from "@/components/Card";
import { Carimbo } from "@/components/Carimbo";
import { BadgeFrescor } from "@/components/Frescor";
import { SeloFonte } from "@/components/SeloFonte";
import { Seletor } from "@/components/Seletor";
import { Esqueleto, ErroBox, Vazio, EmTransicao } from "@/components/Estados";
import { useBalcao } from "@/hooks/useBalcao";
import { caminho, formataReaisCompacto } from "@/lib/api";
import { rotuloMesAAAAMM } from "@/lib/datas";
import { CAPITAIS, UFS } from "@/lib/ufs";
import type {
  Arrecadacao,
  BeneficioSocial,
  CensoCidade,
  FonteDado,
  Municipio,
  NormalizedResponse,
  PibCidade,
} from "@/lib/types";

const inteiro = (v: number | null | undefined) =>
  v == null ? "—" : Math.round(v).toLocaleString("pt-BR");

function KpiCidade({
  rotulo,
  valor,
  detalhe,
  tom = "text-ink",
}: {
  rotulo: string;
  valor: string;
  detalhe?: string;
  tom?: string;
}) {
  return (
    <Card className="p-4 pt-5">
      <p className="kicker mb-2 pl-4">{rotulo}</p>
      <p className={`num pl-4 font-display text-3xl font-semibold leading-none tracking-tight ${tom}`}>
        {valor}
      </p>
      {detalhe && <p className="num mt-1.5 pl-4 text-xs text-muted">{detalhe}</p>}
    </Card>
  );
}

export default function CadernoCidade() {
  const [uf, setUf] = useState("GO");
  const [ibge, setIbge] = useState(CAPITAIS.GO);

  const cidades = useBalcao<NormalizedResponse<Municipio>>(caminho("ibge/municipios", { uf }));
  const censo = useBalcao<NormalizedResponse<CensoCidade>>(caminho("sidra/censo", { municipio: ibge }));
  const pib = useBalcao<NormalizedResponse<PibCidade>>(caminho("sidra/pib", { municipio: ibge }));
  const contas = useBalcao<Arrecadacao>(caminho("arrecadacao", { ente: ibge }));
  const bolsa = useBalcao<NormalizedResponse<BeneficioSocial>>(
    caminho("transparencia/bolsa-familia", { municipio: ibge }),
  );

  const c = censo.dados?.dados?.[0];
  const p = pib.dados?.dados?.[0];
  const fin = contas.dados?.ente ?? null;
  const despesas = (contas.dados?.despesas ?? []).slice(0, 5);
  const folha = bolsa.dados?.dados?.[0];
  const mesFolha = bolsa.dados?.meta?.mes as string | undefined;

  // per capita honesto: PIB do ano dele ÷ população do Censo 2022
  const perCapita = p?.pib && c?.populacao ? Number(p.pib) / c.populacao : null;
  const maxDespesa = despesas.length ? Number(despesas[0].valor) : 1;

  return (
    <div>
      <CadernoHeader
        numero="XXVIII"
        kicker="IBGE + Tesouro + CGU"
        titulo="Minha Cidade"
        resumo="A sua cidade em números oficiais: quanta gente mora (Censo 2022), o tamanho da economia (PIB municipal), o que a prefeitura arrecada e onde gasta (SICONFI) e o Bolsa Família na porta de casa. Escolha o município."
      />

      <div className="mb-6 flex flex-wrap items-center gap-3">
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
          className="max-w-60"
          aria-label="cidade"
        >
          {(cidades.dados?.dados ?? []).map((m) => (
            <option key={m.id} value={String(m.id)}>
              {m.nome}
            </option>
          ))}
        </Seletor>
        {c && (
          <h2 className="font-display text-2xl font-semibold tracking-tight text-ink">
            {c.municipio}
          </h2>
        )}
      </div>

      {/* quem mora aqui */}
      <section>
        <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
          <p className="kicker text-accent">quem mora aqui · Censo 2022</p>
          <Carimbo fonte="IBGE" cache={censo.dados?.meta?.cache as string | undefined} ms={censo.ms} erro={!!censo.erro} />
        </div>
        {censo.erro ? (
          <ErroBox erro={censo.erro} aoTentar={censo.recarregar} />
        ) : censo.carregando && !c ? (
          <Esqueleto linhas={3} />
        ) : c ? (
          <EmTransicao ativo={censo.carregando}>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <KpiCidade rotulo="população" valor={inteiro(c.populacao)} tom="text-accent" />
              <KpiCidade
                rotulo="crescimento"
                valor={c.crescimento_aa_pct != null ? `${c.crescimento_aa_pct.toLocaleString("pt-BR")}%` : "—"}
                detalhe={
                  c.variacao_desde_2010 != null
                    ? `${c.variacao_desde_2010 >= 0 ? "+" : ""}${inteiro(c.variacao_desde_2010)} pessoas desde 2010`
                    : "ao ano, desde 2010"
                }
                tom={c.crescimento_aa_pct != null && c.crescimento_aa_pct < 0 ? "text-erro" : "text-ink"}
              />
              <KpiCidade rotulo="domicílios ocupados" valor={inteiro(c.domicilios)} />
              <KpiCidade
                rotulo="moradores por domicílio"
                valor={c.moradores_por_domicilio?.toLocaleString("pt-BR") ?? "—"}
              />
            </div>
          </EmTransicao>
        ) : (
          <Vazio>sem dados do Censo pra esse município.</Vazio>
        )}
        <SeloFonte fonte={censo.dados?.meta?.fonte as FonteDado | undefined} />
      </section>

      <div className="regua-dupla my-10" />

      {/* a economia */}
      <section>
        <div className="mb-3 flex flex-wrap items-center gap-3">
          <p className="kicker text-accent-2">a economia</p>
          {p && (
            <BadgeFrescor
              rotulo={`contas de ${p.ano}`}
              detalhe="o PIB municipal sai com ~2 anos de defasagem — é o retrato mais novo que existe"
            />
          )}
        </div>
        {pib.erro ? (
          <ErroBox erro={pib.erro} aoTentar={pib.recarregar} />
        ) : pib.carregando && !p ? (
          <Esqueleto linhas={2} />
        ) : p?.pib ? (
          <EmTransicao ativo={pib.carregando}>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <KpiCidade rotulo={`PIB · ${p.ano}`} valor={formataReaisCompacto(p.pib)} tom="text-accent-2" />
              <KpiCidade
                rotulo="PIB por habitante"
                valor={perCapita ? formataReaisCompacto(perCapita) : "—"}
                detalhe={`PIB de ${p.ano} ÷ população do Censo 2022`}
              />
            </div>
          </EmTransicao>
        ) : (
          <Vazio>sem PIB publicado pra esse município.</Vazio>
        )}
        <SeloFonte fonte={pib.dados?.meta?.fonte as FonteDado | undefined} />
      </section>

      <div className="regua-dupla my-10" />

      {/* as contas da prefeitura */}
      <section>
        <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
          <p className="kicker text-ocre">
            as contas da prefeitura{contas.dados?.ano ? ` · ${contas.dados.ano}` : ""}
          </p>
          <Carimbo fonte="SICONFI" ms={contas.ms} erro={!!contas.erro} />
        </div>
        {contas.erro ? (
          <ErroBox erro={contas.erro} aoTentar={contas.recarregar} />
        ) : contas.carregando && !contas.dados ? (
          <Esqueleto linhas={4} />
        ) : fin?.receita_total ? (
          <EmTransicao ativo={contas.carregando}>
            <div className="mb-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
              <KpiCidade rotulo="receita total" valor={formataReaisCompacto(fin.receita_total)} />
              <KpiCidade
                rotulo="arrecadação própria"
                valor={fin.arrecadacao_total ? formataReaisCompacto(fin.arrecadacao_total) : "—"}
                tom="text-ocre"
              />
              <KpiCidade
                rotulo="despesa total"
                valor={fin.despesa_total ? formataReaisCompacto(fin.despesa_total) : "—"}
              />
            </div>
            {despesas.length > 0 && (
              <Card className="p-5 pt-6">
                <p className="kicker mb-4 pl-4">pra onde vai o dinheiro · top {despesas.length} funções</p>
                <ul className="flex flex-col gap-2.5 pl-4">
                  {despesas.map((d, i) => (
                    <li key={d.funcao}>
                      <div className="mb-1 flex items-baseline justify-between gap-3">
                        <span className="min-w-0 truncate text-sm text-ink/85">{d.funcao}</span>
                        <span className={`num shrink-0 text-sm ${i === 0 ? "text-accent" : "text-ink"}`}>
                          {formataReaisCompacto(d.valor)}
                        </span>
                      </div>
                      <div className="h-2 overflow-hidden rounded-sm bg-surface-2">
                        <div
                          className={`h-full rounded-sm ${i === 0 ? "bg-accent" : "bg-ocre/70"}`}
                          style={{ width: `${Math.max((Number(d.valor) / maxDespesa) * 100, 2)}%` }}
                        />
                      </div>
                    </li>
                  ))}
                </ul>
                <p className="mt-4 border-t border-line pt-3 font-editorial text-sm italic text-muted">
                  Quer ver esse dinheiro subindo em tempo real?{" "}
                  <Link href="/arrecadometro" className="text-accent underline decoration-dotted underline-offset-2">
                    Arrecadômetro →
                  </Link>
                </p>
              </Card>
            )}
          </EmTransicao>
        ) : (
          <Vazio>a prefeitura ainda não declarou as contas desse ano no SICONFI.</Vazio>
        )}
        <SeloFonte fonte={contas.dados?.fonte as FonteDado | undefined} />
      </section>

      <div className="regua-dupla my-10" />

      {/* bolsa família */}
      <section>
        <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
          <p className="kicker text-accent">
            Bolsa Família na cidade{mesFolha ? ` · folha de ${rotuloMesAAAAMM(mesFolha)}` : ""}
          </p>
          <Carimbo fonte="CGU" ms={bolsa.ms} erro={!!bolsa.erro} />
        </div>
        {bolsa.erro ? (
          <ErroBox erro={bolsa.erro} aoTentar={bolsa.recarregar} />
        ) : bolsa.carregando && !bolsa.dados ? (
          <Esqueleto linhas={2} />
        ) : folha ? (
          <EmTransicao ativo={bolsa.carregando}>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <KpiCidade rotulo="famílias atendidas" valor={inteiro(folha.beneficiarios)} tom="text-accent" />
              <KpiCidade rotulo="total pago no mês" valor={formataReaisCompacto(folha.valor)} />
              <KpiCidade
                rotulo="média por família"
                valor={
                  folha.beneficiarios
                    ? formataReaisCompacto(Number(folha.valor) / folha.beneficiarios)
                    : "—"
                }
              />
            </div>
          </EmTransicao>
        ) : (
          <Vazio>sem folha publicada pra esse município.</Vazio>
        )}
        <SeloFonte fonte={bolsa.dados?.meta?.fonte as FonteDado | undefined} />
      </section>
    </div>
  );
}
