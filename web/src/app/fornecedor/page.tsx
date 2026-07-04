"use client";

import { useState } from "react";
import { CadernoHeader } from "@/components/Caderno";
import { Card } from "@/components/Card";
import { Carimbo } from "@/components/Carimbo";
import { SeloFonte } from "@/components/SeloFonte";
import { Termo } from "@/components/Termo";
import { Esqueleto, ErroBox, Vazio } from "@/components/Estados";
import { useBalcao } from "@/hooks/useBalcao";
import { caminho, formataData, formataReaisCompacto } from "@/lib/api";
import type { FornecedorOut } from "@/lib/types";

// tradução humana das flags do dossiê da Transparência — as vermelhas pedem
// atenção, as neutras só contam a relação com o governo
const ROTULO_FLAG: Record<string, { rotulo: string; alerta?: boolean }> = {
  favorecidoDespesas: { rotulo: "recebeu pagamentos federais" },
  possuiContratacao: { rotulo: "tem contratos com o governo" },
  convenios: { rotulo: "tem convênios" },
  favorecidoTransferencias: { rotulo: "recebeu transferências" },
  participanteLicitacao: { rotulo: "participou de licitações" },
  emitiuNFe: { rotulo: "emitiu notas fiscais ao governo" },
  beneficiadoRenunciaFiscal: { rotulo: "beneficiado por renúncia fiscal", alerta: true },
  habilitadoRenunciaFiscal: { rotulo: "habilitado a renúncia fiscal" },
  isentoImuneRenunciaFiscal: { rotulo: "isento/imune (renúncia fiscal)" },
  sancionadoCEIS: { rotulo: "SANCIONADO — CEIS", alerta: true },
  sancionadoCNEP: { rotulo: "SANCIONADO — CNEP", alerta: true },
  sancionadoCEPIM: { rotulo: "SANCIONADO — CEPIM", alerta: true },
  sancionadoCEAF: { rotulo: "SANCIONADO — CEAF", alerta: true },
};

const FONTES = [
  {
    nome: "BrasilAPI — dados da Receita Federal",
    url: "https://brasilapi.com.br",
    nota: "Ficha cadastral pública do CNPJ, espelhada da Receita Federal pela BrasilAPI.",
  },
  {
    nome: "Portal da Transparência — CGU",
    url: "https://portaldatransparencia.gov.br",
    nota: "Vínculos com o governo federal, sanções (CEIS/CNEP) e contratos, direto da Controladoria-Geral da União.",
  },
];

const soDigitos = (s: string) => s.replace(/\D/g, "");

function Selo({ texto, alerta }: { texto: string; alerta?: boolean }) {
  return (
    <span
      className={`num inline-flex rounded-full border px-2.5 py-1 text-[0.68rem] uppercase tracking-wider ${
        alerta ? "border-erro/50 bg-erro/10 font-semibold text-erro" : "border-line bg-surface text-ink/80"
      }`}
    >
      {texto}
    </span>
  );
}

function Linha({ rotulo, valor }: { rotulo: string; valor: string | null | undefined }) {
  if (!valor) return null;
  return (
    <div className="flex items-baseline gap-3">
      <span className="kicker w-36 shrink-0">{rotulo}</span>
      <span className="text-sm text-ink/90">{valor}</span>
    </div>
  );
}

export default function CadernoFornecedor() {
  const [cnpj, setCnpj] = useState("");
  const [consultado, setConsultado] = useState("");

  const r = useBalcao<FornecedorOut>(
    consultado ? caminho(`fornecedor/${consultado}`) : null,
  );
  const f = r.dados;

  function consulta(doc: string) {
    const limpo = soDigitos(doc);
    if (limpo.length === 14) setConsultado(limpo);
  }

  return (
    <div>
      <CadernoHeader
        numero="XXVII"
        kicker="Follow the money"
        titulo="Ficha do Fornecedor"
        resumo="Digite um CNPJ e o Balcão cruza quatro consultas numa só: quem é a empresa na Receita, que relação ela tem com o governo federal, se está sancionada e quais contratos já assinou. O caminho do dinheiro público, de ponta a ponta."
      />

      <form
        className="mb-6 flex flex-wrap items-center gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          consulta(cnpj);
        }}
      >
        <input
          value={cnpj}
          onChange={(e) => setCnpj(e.target.value)}
          placeholder="CNPJ (com ou sem máscara)"
          className="num w-full sm:w-72 rounded-md border border-line bg-surface px-3 py-2 text-sm text-ink focus:border-accent focus:outline-none"
        />
        <button
          type="submit"
          disabled={soDigitos(cnpj).length !== 14}
          className="num rounded-md border border-accent bg-accent px-4 py-2 text-xs uppercase tracking-wider text-surface transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
        >
          puxar a ficha
        </button>
        <button
          type="button"
          onClick={() => {
            setCnpj("04.984.400/0001-30");
            consulta("04984400000130");
          }}
          className="num rounded-full border border-line px-3 py-1 text-xs uppercase tracking-wider text-muted transition-colors hover:border-accent hover:text-accent"
        >
          experimente: um táxi aéreo com 15 contratos federais
        </button>
        {consultado && <Carimbo fonte="4 FONTES" ms={r.ms} erro={!!r.erro} />}
      </form>

      {!consultado ? (
        <Vazio>
          a ficha junta Receita Federal, vínculos, <Termo t="ceis">CEIS</Termo>/
          <Termo t="cnep">CNEP</Termo> e contratos federais numa consulta só.
        </Vazio>
      ) : r.erro ? (
        <ErroBox erro={r.erro} aoTentar={r.recarregar} />
      ) : r.carregando && !f ? (
        <Esqueleto linhas={8} />
      ) : f ? (
        <div className="flex flex-col gap-5">
          {/* quem é */}
          <Card className="p-6">
            <p className="kicker mb-3 pl-4">quem é · Receita Federal</p>
            {f.cadastro ? (
              <div className="flex flex-col gap-2 pl-4">
                <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
                  <h2 className="font-display text-2xl font-semibold leading-tight text-ink">
                    {f.cadastro.razao_social}
                  </h2>
                  {f.cadastro.situacao && (
                    <span
                      className={`num text-xs uppercase tracking-wider ${
                        f.cadastro.situacao === "ATIVA" ? "text-emerald-600" : "text-erro"
                      }`}
                    >
                      {f.cadastro.situacao}
                    </span>
                  )}
                </div>
                {f.cadastro.nome_fantasia && (
                  <p className="font-editorial text-sm italic text-muted">
                    “{f.cadastro.nome_fantasia}”
                  </p>
                )}
                <div className="mt-2 flex flex-col gap-1.5">
                  <Linha rotulo="atividade" valor={f.cadastro.atividade} />
                  <Linha rotulo="natureza" valor={f.cadastro.natureza} />
                  <Linha
                    rotulo="desde"
                    valor={f.cadastro.abertura ? formataData(f.cadastro.abertura) : null}
                  />
                  <Linha
                    rotulo="onde"
                    valor={[f.cadastro.municipio, f.cadastro.uf].filter(Boolean).join(" · ") || null}
                  />
                  <Linha
                    rotulo="capital social"
                    valor={f.cadastro.capital_social ? formataReaisCompacto(f.cadastro.capital_social) : null}
                  />
                </div>
                {f.cadastro.socios.length > 0 && (
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    <span className="kicker">sócios</span>
                    {f.cadastro.socios.map((s) => (
                      <span key={s} className="rounded-full border border-line bg-surface px-2.5 py-0.5 text-xs text-ink/80">
                        {s}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <p className="pl-4 font-editorial text-sm italic text-muted">
                {f.erros.cadastro ?? "cadastro indisponível no momento."}
              </p>
            )}
          </Card>

          {/* vínculos */}
          <Card className="p-6">
            <p className="kicker mb-3 pl-4">relação com o governo federal · CGU</p>
            {f.vinculos ? (
              f.vinculos.vinculos.length ? (
                <div className="flex flex-wrap gap-2 pl-4">
                  {f.vinculos.vinculos.map((v) => {
                    const t = ROTULO_FLAG[v];
                    return <Selo key={v} texto={t?.rotulo ?? v} alerta={t?.alerta} />;
                  })}
                </div>
              ) : (
                <p className="pl-4 font-editorial text-sm italic text-muted">
                  nenhum vínculo registrado com o governo federal.
                </p>
              )
            ) : (
              <p className="pl-4 font-editorial text-sm italic text-muted">
                {f.erros.vinculos ?? "sem vínculos registrados com o governo federal."}
              </p>
            )}
          </Card>

          {/* sanções */}
          <Card className="p-6">
            <p className="kicker mb-3 pl-4">
              sanções · <Termo t="ceis">CEIS</Termo> e <Termo t="cnep">CNEP</Termo>
            </p>
            {f.erros.sancoes ? (
              <p className="pl-4 font-editorial text-sm italic text-muted">{f.erros.sancoes}</p>
            ) : f.sancoes.length ? (
              <div className="flex flex-col gap-3 pl-4">
                {f.sancoes.map((s, i) => (
                  <div key={i} className="rounded-md border border-erro/40 bg-erro/5 p-3">
                    <p className="num text-xs uppercase tracking-wider text-erro">
                      {s.cadastro} · {s.tipo ?? "sanção"}
                    </p>
                    <p className="mt-1 text-sm text-ink/85">
                      {[s.orgao, s.uf].filter(Boolean).join(" · ")}
                      {s.inicio && ` · desde ${formataData(s.inicio)}`}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="pl-4 text-sm text-emerald-600">
                Nada consta. <span className="text-muted">Não aparece no CEIS nem no CNEP.</span>
              </p>
            )}
          </Card>

          {/* contratos */}
          <Card className="p-6">
            <p className="kicker mb-3 flex items-baseline justify-between gap-3 pl-4">
              <span>contratos com o governo federal</span>
              {f.contratos.length > 0 && (
                <span className="num normal-case tracking-normal text-ink">
                  {f.contratos.length}
                  {Boolean(f.meta.contratos_tem_proxima) && "+"}
                </span>
              )}
            </p>
            {f.erros.contratos ? (
              <p className="pl-4 font-editorial text-sm italic text-muted">{f.erros.contratos}</p>
            ) : f.contratos.length ? (
              <div className="flex flex-col divide-y divide-line pl-4">
                {f.contratos.map((c, i) => (
                  <div key={i} className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 py-2.5">
                    <div className="min-w-0 flex-1">
                      <p className="text-sm leading-snug text-ink/90">{c.objeto}</p>
                      <p className="num mt-0.5 text-xs text-muted">
                        {[c.orgao, c.modalidade, c.situacao].filter(Boolean).join(" · ")}
                        {c.inicio && ` · ${formataData(c.inicio)}`}
                        {c.fim && ` → ${formataData(c.fim)}`}
                      </p>
                    </div>
                    {c.valor && (
                      <span className="num shrink-0 text-sm font-semibold text-ink">
                        {formataReaisCompacto(c.valor)}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="pl-4 font-editorial text-sm italic text-muted">
                nenhum contrato federal encontrado pra este CNPJ.
              </p>
            )}
          </Card>
        </div>
      ) : null}

      {consultado && (
        <>
          <SeloFonte fonte={FONTES[0]} />
          <SeloFonte fonte={FONTES[1]} />
        </>
      )}
    </div>
  );
}
