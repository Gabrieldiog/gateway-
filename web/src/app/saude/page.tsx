"use client";

import { useEffect, useState } from "react";
import { CadernoHeader } from "@/components/Caderno";
import { Card } from "@/components/Card";
import { Carimbo } from "@/components/Carimbo";
import { Seletor } from "@/components/Seletor";
import { Esqueleto, ErroBox, Vazio, EmTransicao } from "@/components/Estados";
import { useBalcao } from "@/hooks/useBalcao";
import { caminho } from "@/lib/api";
import { UFS } from "@/lib/ufs";
import type { Estabelecimento, NormalizedResponse } from "@/lib/types";

// os tipos mais procurados do CNES; o código é o que o filtro espera
const TIPOS = [
  { cod: "", nome: "todos" },
  { cod: "5", nome: "hospital geral" },
  { cod: "7", nome: "hospital especializado" },
  { cod: "2", nome: "UBS / centro de saúde" },
  { cod: "1", nome: "posto de saúde" },
  { cod: "73", nome: "pronto atendimento" },
  { cod: "20", nome: "pronto-socorro" },
  { cod: "36", nome: "clínica / especialidade" },
  { cod: "70", nome: "CAPS (psicossocial)" },
];

const LIMITE = 20;

const CORES_ESFERA: Record<string, string> = {
  MUNICIPAL: "text-accent-2 border-accent-2/40",
  ESTADUAL: "text-accent border-accent/40",
  FEDERAL: "text-ink border-ink/30",
};

export default function CadernoSaude() {
  const [uf, setUf] = useState("SP");
  const [tipo, setTipo] = useState("5");
  const [pagina, setPagina] = useState(1);

  // volta pra primeira página quando o filtro muda
  useEffect(() => setPagina(1), [uf, tipo]);

  const lista = useBalcao<NormalizedResponse<Estabelecimento>>(
    caminho("sus/estabelecimentos", { uf, tipo: tipo || undefined, limite: LIMITE, pagina }),
  );
  const estabs = lista.dados?.dados ?? [];
  const temProxima = Boolean(lista.dados?.meta?.tem_proxima);

  return (
    <div>
      <CadernoHeader
        numero="VII"
        kicker="Ministério da Saúde · CNES"
        titulo="Os estabelecimentos do SUS"
        resumo="Mais de 350 mil unidades de saúde do país — hospitais, UBS, prontos-socorros — filtráveis por estado e tipo. Cada uma com tipo, esfera administrativa, endereço e CNPJ."
      />

      <div className="mb-6 flex flex-wrap items-center gap-4">
        <label className="num flex items-center gap-2 text-xs uppercase tracking-wider text-muted">
          UF
          <Seletor value={uf} onChange={(e) => setUf(e.target.value)}>
            {UFS.map((u) => (
              <option key={u} value={u}>
                {u}
              </option>
            ))}
          </Seletor>
        </label>
        <label className="num flex items-center gap-2 text-xs uppercase tracking-wider text-muted">
          Tipo
          <Seletor value={tipo} onChange={(e) => setTipo(e.target.value)}>
            {TIPOS.map((t) => (
              <option key={t.cod} value={t.cod}>
                {t.nome}
              </option>
            ))}
          </Seletor>
        </label>
      </div>

      <div className="mb-3 flex items-center justify-between">
        <p className="kicker">
          {lista.carregando && !lista.dados
            ? "consultando…"
            : `${estabs.length} no ${uf} · página ${pagina}`}
        </p>
        <Carimbo
          fonte="SUS"
          cache={lista.dados?.meta?.cache as string | undefined}
          ms={lista.ms}
          erro={!!lista.erro}
        />
      </div>

      {lista.erro ? (
        <ErroBox erro={lista.erro} aoTentar={lista.recarregar} />
      ) : lista.carregando && !lista.dados ? (
        <Esqueleto linhas={8} />
      ) : estabs.length === 0 ? (
        <Vazio>nenhum estabelecimento para esse filtro.</Vazio>
      ) : (
        <EmTransicao ativo={lista.carregando}>
        <ul className="flex flex-col gap-2">
          {estabs.map((e) => (
            <li key={e.cnes}>
              <Card className="p-4 pl-7">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <span className="block truncate text-ink" title={e.nome}>
                      {e.nome}
                    </span>
                    <span className="num text-xs text-muted">
                      {[e.tipo?.toLowerCase(), e.bairro?.toLowerCase(), e.uf]
                        .filter(Boolean)
                        .join(" · ")}
                    </span>
                  </div>
                  {e.esfera && (
                    <span
                      className={`num shrink-0 rounded-sm border px-1.5 py-0.5 text-[0.6rem] uppercase tracking-wider ${
                        CORES_ESFERA[e.esfera] ?? "text-muted border-line"
                      }`}
                    >
                      {e.esfera}
                    </span>
                  )}
                </div>
                {e.cnpj && (
                  <span className="num mt-1 block text-xs text-muted">CNPJ {e.cnpj}</span>
                )}
              </Card>
            </li>
          ))}
        </ul>
        </EmTransicao>
      )}

      {lista.dados && estabs.length > 0 && (
        <div className="mt-5 flex items-center justify-between">
          <button
            onClick={() => setPagina((p) => Math.max(1, p - 1))}
            disabled={pagina === 1}
            className="num rounded-md border border-line px-3 py-1 text-xs uppercase tracking-wider text-ink transition-colors hover:bg-surface-2 disabled:cursor-not-allowed disabled:opacity-40"
          >
            ← anterior
          </button>
          <span className="num text-xs text-muted">página {pagina}</span>
          <button
            onClick={() => setPagina((p) => p + 1)}
            disabled={!temProxima}
            className="num rounded-md border border-line px-3 py-1 text-xs uppercase tracking-wider text-ink transition-colors hover:bg-surface-2 disabled:cursor-not-allowed disabled:opacity-40"
          >
            próxima →
          </button>
        </div>
      )}
    </div>
  );
}
