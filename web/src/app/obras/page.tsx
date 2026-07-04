"use client";

import { useState } from "react";
import { CadernoHeader } from "@/components/Caderno";
import { Card } from "@/components/Card";
import { Carimbo } from "@/components/Carimbo";
import { LerMais } from "@/components/LerMais";
import { SeloFonte } from "@/components/SeloFonte";
import { Seletor } from "@/components/Seletor";
import { Esqueleto, ErroBox, Vazio, EmTransicao } from "@/components/Estados";
import { useBalcao } from "@/hooks/useBalcao";
import { BalcaoError, caminho, formataData, formataReaisCompacto } from "@/lib/api";
import { UFS } from "@/lib/ufs";
import type { FonteDado, NormalizedResponse, ObraDinheiroOut, ObraPublica } from "@/lib/types";

const SITUACOES: [string, string][] = [
  ["paralisada", "Paralisadas"],
  ["execucao", "Em execução"],
  ["concluida", "Concluídas"],
  ["cadastrada", "Cadastradas"],
];

function formataCnpj(doc: string | null | undefined): string | null {
  if (!doc || doc.length !== 14) return null;
  return `${doc.slice(0, 2)}.${doc.slice(2, 5)}.${doc.slice(5, 8)}/${doc.slice(8, 12)}-${doc.slice(12)}`;
}

// como cada favorecido foi descoberto — a cascata explicada em meia palavra
const ORIGEM: Record<string, string> = {
  siafi: "confirmado no SIAFI",
  repasse: "repasse ao executor",
  obrasgov: "informado pela fonte",
};

// o follow-the-money da obra: quem construiu e pra quem o dinheiro saiu,
// resolvido em cascata (Obrasgov → regra orçamentária → SICONV → SIAFI)
function DinheiroDaObra({ id }: { id: string }) {
  const r = useBalcao<ObraDinheiroOut>(caminho("obra/dinheiro", { id }));
  const empenhos = r.dados?.empenhos ?? [];
  const contratos = r.dados?.contratos ?? [];
  const total = r.dados?.total_empenhado;
  const erros = r.dados?.erros ?? {};
  const mensagensDeErro = Object.values(erros);

  if (r.erro) return <ErroBox erro={r.erro} aoTentar={r.recarregar} />;
  if (r.carregando && !r.dados) return <Esqueleto linhas={3} />;
  if (!empenhos.length && !contratos.length) {
    // vazio POR FALHA não é vazio de verdade: erro com retry, não afirmação
    if (mensagensDeErro.length) {
      return (
        <ErroBox
          erro={new BalcaoError(mensagensDeErro.join(" · "), 502, { passageiro: true })}
          aoTentar={r.recarregar}
        />
      );
    }
    return (
      <p className="font-editorial text-sm italic text-muted">
        nenhum empenho ou contrato registrado — o dinheiro ainda não começou a sair (ou o órgão
        não informou).
      </p>
    );
  }
  return (
    <div className="flex flex-col gap-4">
      {mensagensDeErro.length > 0 && (
        <p className="font-editorial text-xs italic text-muted">
          parte das fontes falhou agora ({mensagensDeErro.join(" · ")}) — o que está aqui pode
          estar incompleto.{" "}
          <button onClick={r.recarregar} className="not-italic text-accent hover:underline">
            tentar de novo
          </button>
        </p>
      )}
      {contratos.length > 0 && (
        <div className="rounded-md border border-accent/25 bg-accent/4 p-3">
          <p className="kicker mb-1.5 text-accent">quem construiu</p>
          {contratos.map((c, i) => (
            <div key={i} className={i > 0 ? "mt-2 border-t border-line/60 pt-2" : ""}>
              <p className="text-sm font-semibold text-ink">
                {c.fornecedor ?? "fornecedor não informado"}
                {c.valor && (
                  <span className="num ml-2 font-normal">{formataReaisCompacto(c.valor)}</span>
                )}
              </p>
              <p className="num mt-0.5 flex flex-wrap gap-x-3 text-xs text-muted">
                {formataCnpj(c.cnpj) && <span>CNPJ {formataCnpj(c.cnpj)}</span>}
                {c.modalidade_licitacao && <span>{c.modalidade_licitacao}</span>}
                {c.numero && <span>contrato {c.numero}</span>}
                {c.assinatura && <span>assinado em {formataData(c.assinatura)}</span>}
                {c.situacao && <span>{c.situacao.toLowerCase()}</span>}
              </p>
            </div>
          ))}
        </div>
      )}
      {empenhos.length > 0 && (
        <div>
          {total && Number(total) > 0 && (
            <p className="kicker mb-2">
              já empenhado:{" "}
              <span className="num normal-case tracking-normal text-ink">
                {formataReaisCompacto(total)}
                {r.dados?.tem_mais_empenhos && "+"}
              </span>
            </p>
          )}
          <ul className="flex flex-col divide-y divide-line/60">
            {empenhos.map((e, i) => (
              <li key={i} className="py-1.5">
                <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-0.5">
                  <span className="min-w-0 flex-1 truncate text-sm text-ink/85">
                    {e.favorecido ??
                      (e.origem === "interno"
                        ? "movimentação interna do governo"
                        : "favorecido não informado pela fonte")}
                  </span>
                  <span className="num shrink-0 text-sm text-ink">
                    {e.valor ? formataReaisCompacto(e.valor) : "—"}
                  </span>
                </div>
                <p className="num flex flex-wrap gap-x-3 text-[0.7rem] text-muted">
                  {e.origem && ORIGEM[e.origem] && <span>{ORIGEM[e.origem]}</span>}
                  {e.modalidade && <span>{e.modalidade}</span>}
                  {e.data && <span>{formataData(e.data)}</span>}
                  {e.nota && <span>{e.nota}</span>}
                  {e.autor_emenda && (
                    <span className="text-accent">emenda de {e.autor_emenda}</span>
                  )}
                </p>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// cor do carimbo de situação — parada é vermelho, andando é verde
function corSituacao(s: string | null): string {
  if (s === "Paralisada") return "bg-erro/10 text-erro";
  if (s === "Em execução") return "bg-ok/10 text-ok";
  if (s === "Concluída") return "bg-surface-2 text-muted";
  return "bg-accent-2/10 text-accent-2";
}

export default function CadernoObras() {
  const [situacao, setSituacao] = useState("paralisada");
  const [uf, setUf] = useState("");
  const [pagina, setPagina] = useState(1);
  const [aberta, setAberta] = useState<string | null>(null);

  const r = useBalcao<NormalizedResponse<ObraPublica>>(
    caminho("obrasgov/obras", { situacao, uf: uf || undefined, pagina }),
  );
  const obras = r.dados?.dados ?? [];
  const temProxima = Boolean(r.dados?.meta?.tem_proxima);
  const fonte = r.dados?.meta?.fonte as FonteDado | undefined;

  return (
    <div>
      <CadernoHeader
        numero="XXX"
        kicker="Obrasgov · Ministério da Gestão"
        titulo="Obras Públicas"
        resumo="Toda obra com dinheiro federal, do cadastro oficial — com situação, valores e datas previstas. Comece pelas paralisadas: quando o prazo já passou e a obra parou, o selo de atraso acende sozinho."
      />

      <div className="mb-6 flex flex-wrap items-center gap-3">
        <div className="inline-flex gap-0.5 rounded-md border border-line p-0.5">
          {SITUACOES.map(([v, label]) => (
            <button
              key={v}
              onClick={() => {
                setSituacao(v);
                setPagina(1);
              }}
              aria-pressed={situacao === v}
              className={`num rounded px-3 py-1 text-xs uppercase tracking-wider transition-colors ${
                situacao === v ? "bg-accent/15 font-semibold text-accent" : "text-muted hover:text-ink"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        <Seletor
          value={uf}
          onChange={(e) => {
            setUf(e.target.value);
            setPagina(1);
          }}
          aria-label="estado"
        >
          <option value="">Brasil todo</option>
          {UFS.map((u) => (
            <option key={u}>{u}</option>
          ))}
        </Seletor>
        <Carimbo fonte="OBRASGOV" cache={r.dados?.meta?.cache as string | undefined} ms={r.ms} erro={!!r.erro} />
      </div>

      {r.erro ? (
        <ErroBox erro={r.erro} aoTentar={r.recarregar} />
      ) : r.carregando && !r.dados ? (
        <Esqueleto linhas={8} />
      ) : obras.length ? (
        <EmTransicao ativo={r.carregando}>
          <div className="flex flex-col gap-4">
            {obras.map((o) => (
              <Card key={o.id} className="p-5">
                <div className="mb-1.5 flex flex-wrap items-center gap-2">
                  <span
                    className={`num rounded-full px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wider ${corSituacao(o.situacao)}`}
                  >
                    {o.situacao ?? "sem situação"}
                  </span>
                  {o.atrasada && (
                    <span className="num rounded-full bg-erro px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wider text-white">
                      atrasada
                    </span>
                  )}
                  {o.especie && <span className="num text-xs text-muted">{o.especie}</span>}
                  {o.uf && <span className="num text-xs text-muted">· {o.uf}</span>}
                </div>
                <h3 className="font-display text-lg font-semibold leading-snug text-ink">
                  {o.nome}
                </h3>
                {o.descricao && o.descricao !== o.nome && (
                  <LerMais
                    texto={o.descricao}
                    limite={180}
                    className="mt-1 font-editorial text-sm leading-relaxed text-ink/75"
                  />
                )}
                <div className="num mt-2 flex flex-wrap gap-x-5 gap-y-1 text-xs text-muted">
                  <span className={o.valor_previsto ? "text-ink" : ""}>
                    {o.valor_previsto
                      ? `previsto ${formataReaisCompacto(o.valor_previsto)}`
                      : "valor não informado pela fonte"}
                  </span>
                  {o.inicio_previsto && <span>início previsto {formataData(o.inicio_previsto)}</span>}
                  {o.fim_previsto && (
                    <span className={o.atrasada ? "font-semibold text-erro" : ""}>
                      entrega prevista {formataData(o.fim_previsto)}
                    </span>
                  )}
                  {o.fim_efetivo && <span className="text-ok">entregue em {formataData(o.fim_efetivo)}</span>}
                  {o.executor && <span>executor: {o.executor}</span>}
                  {o.empregos != null && <span>{o.empregos.toLocaleString("pt-BR")} empregos</span>}
                  {o.populacao_beneficiada != null && (
                    <span>{o.populacao_beneficiada.toLocaleString("pt-BR")} beneficiados</span>
                  )}
                  <button
                    onClick={() => setAberta(aberta === o.id ? null : o.id)}
                    aria-expanded={aberta === o.id}
                    className="uppercase tracking-wider text-accent transition-colors hover:text-accent-2"
                  >
                    {aberta === o.id ? "fechar ▴" : "o dinheiro que já saiu ▸"}
                  </button>
                </div>
                {aberta === o.id && (
                  <div className="mt-3 border-t border-line pt-3">
                    <DinheiroDaObra id={o.id} />
                  </div>
                )}
              </Card>
            ))}
          </div>
          <div className="mt-5 flex items-center gap-3">
            <button
              onClick={() => setPagina((p) => Math.max(1, p - 1))}
              disabled={pagina <= 1}
              className="num inline-flex min-h-9 items-center rounded-md border border-line px-3.5 py-1.5 text-xs uppercase tracking-wider text-ink transition-colors hover:bg-surface-2 disabled:cursor-not-allowed disabled:opacity-40"
            >
              ← anteriores
            </button>
            <span className="num text-xs text-muted">página {pagina}</span>
            <button
              onClick={() => setPagina((p) => p + 1)}
              disabled={!temProxima}
              className="num inline-flex min-h-9 items-center rounded-md border border-line px-3.5 py-1.5 text-xs uppercase tracking-wider text-ink transition-colors hover:bg-surface-2 disabled:cursor-not-allowed disabled:opacity-40"
            >
              próximas →
            </button>
          </div>
        </EmTransicao>
      ) : (
        <Vazio>nenhuma obra com esses filtros.</Vazio>
      )}

      <SeloFonte fonte={fonte} />
    </div>
  );
}
