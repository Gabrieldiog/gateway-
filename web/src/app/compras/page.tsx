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
import { UFS } from "@/lib/ufs";
import type { ContratoPublico, FonteDado, Licitacao, NormalizedResponse } from "@/lib/types";

type Aba = "licitacoes" | "contratos";

const MODALIDADES = [
  ["pregao-eletronico", "Pregão eletrônico"],
  ["dispensa", "Dispensa"],
  ["concorrencia-eletronica", "Concorrência"],
  ["inexigibilidade", "Inexigibilidade"],
  ["credenciamento", "Credenciamento"],
] as const;

function Paginacao({
  pagina,
  temProxima,
  muda,
}: {
  pagina: number;
  temProxima: boolean;
  muda: (p: number) => void;
}) {
  return (
    <div className="mt-4 flex items-center gap-3">
      <button
        onClick={() => muda(Math.max(1, pagina - 1))}
        disabled={pagina <= 1}
        className="num rounded-md border border-line px-3 py-1 text-xs uppercase tracking-wider text-ink transition-colors hover:bg-surface-2 disabled:opacity-40"
      >
        ← anterior
      </button>
      <span className="num text-xs text-muted">página {pagina}</span>
      <button
        onClick={() => muda(pagina + 1)}
        disabled={!temProxima}
        className="num rounded-md border border-line px-3 py-1 text-xs uppercase tracking-wider text-ink transition-colors hover:bg-surface-2 disabled:opacity-40"
      >
        próxima →
      </button>
    </div>
  );
}

function Licitacoes() {
  const [modalidade, setModalidade] = useState<string>("pregao-eletronico");
  const [uf, setUf] = useState("");
  const [pagina, setPagina] = useState(1);

  const r = useBalcao<NormalizedResponse<Licitacao>>(
    caminho("pncp/licitacoes", { modalidade, uf: uf || undefined, pagina }),
  );
  const linhas = r.dados?.dados ?? [];
  const total = r.dados?.meta?.total_registros as number | undefined;
  const fonte = r.dados?.meta?.fonte as FonteDado | undefined;

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <Seletor
          value={modalidade}
          onChange={(e) => {
            setModalidade(e.target.value);
            setPagina(1);
          }}
          aria-label="modalidade"
        >
          {MODALIDADES.map(([v, label]) => (
            <option key={v} value={v}>
              {label}
            </option>
          ))}
        </Seletor>
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
        <Carimbo fonte="PNCP" cache={r.dados?.meta?.cache as string | undefined} ms={r.ms} erro={!!r.erro} />
      </div>

      {total != null && (
        <p className="kicker mb-3">
          <span className="num text-ink">{total.toLocaleString("pt-BR")}</span> contratações publicadas
          nos últimos 7 dias nesse recorte
        </p>
      )}

      {r.erro ? (
        <ErroBox erro={r.erro} aoTentar={r.recarregar} />
      ) : r.carregando && !r.dados ? (
        <Esqueleto linhas={8} />
      ) : linhas.length ? (
        <EmTransicao ativo={r.carregando}>
          <Card className="divide-y divide-line p-0">
            {linhas.map((l) => (
              <div key={l.numero_controle} className="px-5 py-3">
                <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                  <p className="min-w-0 flex-1 truncate text-sm font-semibold text-ink" title={l.orgao}>
                    {l.orgao}
                    <span className="num ml-2 text-xs font-normal text-muted">
                      {[l.municipio, l.uf].filter(Boolean).join("/")}
                      {l.esfera && ` · ${l.esfera}`}
                    </span>
                  </p>
                  <span className="num shrink-0 text-sm text-accent">
                    {l.valor_estimado ? formataReaisCompacto(l.valor_estimado) : "—"}
                  </span>
                </div>
                <p className="mt-1 line-clamp-2 font-editorial text-sm leading-snug text-ink/80" title={l.objeto}>
                  {l.objeto}
                </p>
                <p className="num mt-1 text-xs text-muted">
                  {l.modalidade}
                  {l.propostas_ate && (
                    <span className="ml-2 text-ok">propostas até {formataData(l.propostas_ate)}</span>
                  )}
                </p>
              </div>
            ))}
          </Card>
          <Paginacao
            pagina={pagina}
            temProxima={Boolean(r.dados?.meta?.tem_proxima)}
            muda={setPagina}
          />
        </EmTransicao>
      ) : (
        <Vazio>nenhuma contratação nesse recorte na última semana.</Vazio>
      )}
      <SeloFonte fonte={fonte} />
    </div>
  );
}

function Contratos() {
  const [pagina, setPagina] = useState(1);

  const r = useBalcao<NormalizedResponse<ContratoPublico>>(
    caminho("pncp/contratos", { pagina }),
  );
  const linhas = r.dados?.dados ?? [];
  const total = r.dados?.meta?.total_registros as number | undefined;
  const fonte = r.dados?.meta?.fonte as FonteDado | undefined;

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        {total != null && (
          <p className="kicker">
            <span className="num text-ink">{total.toLocaleString("pt-BR")}</span> contratos assinados nos
            últimos 7 dias
          </p>
        )}
        <Carimbo fonte="PNCP" cache={r.dados?.meta?.cache as string | undefined} ms={r.ms} erro={!!r.erro} />
      </div>

      {r.erro ? (
        <ErroBox erro={r.erro} aoTentar={r.recarregar} />
      ) : r.carregando && !r.dados ? (
        <Esqueleto linhas={8} />
      ) : linhas.length ? (
        <EmTransicao ativo={r.carregando}>
          <Card className="divide-y divide-line p-0">
            {linhas.map((c) => (
              <div key={c.numero_controle} className="px-5 py-3">
                <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                  <p className="min-w-0 flex-1 truncate text-sm text-ink" title={`${c.orgao} → ${c.fornecedor}`}>
                    <span className="font-semibold">{c.orgao}</span>
                    <span className="mx-1.5 text-muted">→</span>
                    {c.fornecedor}
                  </p>
                  <span className="num shrink-0 text-sm text-accent">
                    {c.valor ? formataReaisCompacto(c.valor) : "—"}
                  </span>
                </div>
                <p className="mt-1 line-clamp-2 font-editorial text-sm leading-snug text-ink/80" title={c.objeto}>
                  {c.objeto}
                </p>
                <p className="num mt-1 text-xs text-muted">
                  {[c.municipio, c.uf].filter(Boolean).join("/")}
                  {c.assinado_em && ` · assinado em ${formataData(c.assinado_em)}`}
                  {c.vigencia_fim && ` · vigência até ${formataData(c.vigencia_fim)}`}
                </p>
              </div>
            ))}
          </Card>
          <Paginacao
            pagina={pagina}
            temProxima={Boolean(r.dados?.meta?.tem_proxima)}
            muda={setPagina}
          />
        </EmTransicao>
      ) : (
        <Vazio>nenhum contrato na última semana.</Vazio>
      )}
      <SeloFonte fonte={fonte} />
    </div>
  );
}

export default function CadernoCompras() {
  const [aba, setAba] = useState<Aba>("licitacoes");

  return (
    <div>
      <CadernoHeader
        numero="XXIII"
        kicker="PNCP · Lei 14.133"
        titulo="Compras públicas"
        resumo="O que o governo — União, estados e municípios — está comprando agora: as licitações abertas a propostas e os contratos recém-assinados, do Portal Nacional de Contratações Públicas."
      />

      <div className="mb-6 inline-flex gap-0.5 rounded-md border border-line p-0.5">
        {(
          [
            ["licitacoes", "Licitações"],
            ["contratos", "Contratos"],
          ] as [Aba, string][]
        ).map(([v, label]) => (
          <button
            key={v}
            onClick={() => setAba(v)}
            aria-pressed={aba === v}
            className={`num rounded px-3 py-1 text-xs uppercase tracking-wider transition-colors ${
              aba === v ? "bg-accent/15 font-semibold text-accent" : "text-muted hover:text-ink"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {aba === "licitacoes" ? <Licitacoes /> : <Contratos />}
    </div>
  );
}
