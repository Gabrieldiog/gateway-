"use client";

import { useState } from "react";
import { CadernoHeader } from "@/components/Caderno";
import { Card } from "@/components/Card";
import { Carimbo } from "@/components/Carimbo";
import { BadgeFrescor } from "@/components/Frescor";
import { SeloFonte } from "@/components/SeloFonte";
import { Esqueleto, ErroBox, Vazio, EmTransicao } from "@/components/Estados";
import { useBalcao } from "@/hooks/useBalcao";
import { caminho, formataData } from "@/lib/api";
import type { FonteDado, NormalizedResponse, TituloPublico } from "@/lib/types";

const brl = (v: string | null) =>
  v == null ? "—" : `R$ ${Number(v).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

const pct = (v: string | null) =>
  v == null ? "—" : `${Number(v).toLocaleString("pt-BR", { maximumFractionDigits: 2 })}%`;

export default function CadernoTitulos() {
  const [tipo, setTipo] = useState("");

  const r = useBalcao<NormalizedResponse<TituloPublico>>(caminho("tesourodireto/titulos"));
  const todos = r.dados?.dados ?? [];
  const tipos = [...new Set(todos.map((t) => t.tipo))];
  const titulos = tipo ? todos.filter((t) => t.tipo === tipo) : todos;
  const fonte = r.dados?.meta?.fonte as FonteDado | undefined;
  const dataBase = r.dados?.meta?.data as string | undefined;

  return (
    <div>
      <CadernoHeader
        numero="XXII"
        kicker="Tesouro Nacional"
        titulo="Títulos públicos"
        resumo="A taxa e o preço do dia de cada título do Tesouro Direto — Selic, IPCA+, Prefixado, Educa+ e Renda+. O Balcão garimpa a foto mais recente de um arquivo histórico de 14 MB sem ordem nenhuma."
      />

      <div className="mb-5 flex flex-wrap items-center gap-2">
        <button
          onClick={() => setTipo("")}
          aria-pressed={tipo === ""}
          className={`num rounded-full border px-3 py-1 text-xs uppercase tracking-wider transition-colors ${
            tipo === "" ? "border-accent bg-accent text-surface" : "border-line text-muted hover:border-accent hover:text-accent"
          }`}
        >
          todos
        </button>
        {tipos.map((t) => (
          <button
            key={t}
            onClick={() => setTipo(t)}
            aria-pressed={tipo === t}
            className={`num rounded-full border px-3 py-1 text-xs uppercase tracking-wider transition-colors ${
              tipo === t ? "border-accent bg-accent text-surface" : "border-line text-muted hover:border-accent hover:text-accent"
            }`}
          >
            {t.replace("Tesouro ", "")}
          </button>
        ))}
        <span className="mx-1 h-4 w-px bg-line" />
        <Carimbo fonte="TESOURO" cache={r.dados?.meta?.cache as string | undefined} ms={r.ms} erro={!!r.erro} />
      </div>

      <div className="mb-3 flex flex-wrap items-center gap-3">
        <BadgeFrescor
          rotulo="atualizado diariamente"
          detalhe={dataBase ? `preços da manhã de ${formataData(dataBase)}` : undefined}
        />
      </div>

      {r.erro ? (
        <ErroBox erro={r.erro} aoTentar={r.recarregar} />
      ) : r.carregando && !r.dados ? (
        <Esqueleto linhas={10} />
      ) : titulos.length ? (
        <EmTransicao ativo={r.carregando}>
          <Card className="max-h-[75vh] overflow-auto p-0">
            <table className="w-full text-sm">
              <thead className="grudento">
                <tr className="border-b border-line text-left">
                  <th className="kicker px-5 py-3 font-normal">título</th>
                  <th className="kicker px-3 py-3 text-right font-normal">vence em</th>
                  <th className="kicker px-3 py-3 text-right font-normal">taxa (a.a.)</th>
                  <th className="kicker px-5 py-3 text-right font-normal">preço (PU)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {titulos.map((t) => (
                  <tr key={`${t.tipo}-${t.vencimento}`}>
                    <td className="px-5 py-2.5 font-semibold text-ink">{t.nome}</td>
                    <td className="num px-3 py-2.5 text-right text-muted">{formataData(t.vencimento)}</td>
                    <td className="num px-3 py-2.5 text-right text-accent-2">{pct(t.taxa_compra)}</td>
                    <td className="num px-5 py-2.5 text-right text-ink">{brl(t.pu_compra)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="border-t border-line px-5 py-3 font-editorial text-sm italic text-muted">
              Taxa e preço de compra da manhã. IPCA+ paga a taxa além da inflação; o Prefixado trava a
              taxa cheia. Não é recomendação de investimento.
            </p>
          </Card>
        </EmTransicao>
      ) : (
        <Vazio>nenhum título nesse filtro.</Vazio>
      )}

      <SeloFonte fonte={fonte} />
    </div>
  );
}
