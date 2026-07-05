"use client";

import { useState } from "react";
import { CadernoHeader } from "@/components/Caderno";
import { Card } from "@/components/Card";
import { Carimbo } from "@/components/Carimbo";
import { SeloFonte } from "@/components/SeloFonte";
import { Seletor } from "@/components/Seletor";
import { Termo } from "@/components/Termo";
import { LerMais } from "@/components/LerMais";
import { Esqueleto, ErroBox, Vazio, EmTransicao } from "@/components/Estados";
import { useBalcao } from "@/hooks/useBalcao";
import { caminho, formataBRL, formataData, formataReaisCompacto } from "@/lib/api";
import { UFS } from "@/lib/ufs";
import type {
  ArquivoCompra,
  ContratoPublico,
  FonteDado,
  ItemCompra,
  Licitacao,
  NormalizedResponse,
  VencedorItem,
} from "@/lib/types";

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
    <div className="mt-4 flex flex-wrap items-center gap-3">
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

// o vencedor de um item, buscado só quando alguém pergunta
function Vencedor({ controle, item }: { controle: string; item: number }) {
  const r = useBalcao<NormalizedResponse<VencedorItem>>(
    caminho("pncp/resultado", { controle, item }),
  );
  const vencedores = r.dados?.dados ?? [];
  const aviso = r.dados?.meta?.aviso as string | undefined;

  if (r.erro) return <ErroBox erro={r.erro} aoTentar={r.recarregar} />;
  if (r.carregando && !r.dados) return <Esqueleto linhas={2} />;
  if (!vencedores.length) {
    return (
      <p className="font-editorial text-sm italic text-muted">
        {aviso ?? "item ainda sem resultado homologado."}
      </p>
    );
  }
  return (
    <div className="flex flex-col gap-2">
      {vencedores.map((v, i) => (
        <div key={`${v.fornecedor}-${i}`} className="rounded-md bg-surface-2/60 px-3 py-2">
          <p className="text-sm text-ink">
            <span className="font-semibold">{v.fornecedor}</span>
            {v.porte && <span className="num ml-2 text-xs text-muted">{v.porte}</span>}
          </p>
          <p className="num mt-0.5 text-xs text-muted">
            {v.valor_total && (
              <span className="text-ink">homologado por {formataBRL(v.valor_total)}</span>
            )}
            {v.desconto_pct != null && v.desconto_pct > 0 && (
              <span className="ml-2 text-emerald-600">
                {v.desconto_pct.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}% abaixo do
                estimado
              </span>
            )}
            {v.data && <span className="ml-2">· {formataData(v.data)}</span>}
          </p>
        </div>
      ))}
    </div>
  );
}

// os documentos da compra — o edital em PDF é o "ler tudo" de verdade
function ArquivosDaCompra({ controle }: { controle: string }) {
  const r = useBalcao<NormalizedResponse<ArquivoCompra>>(caminho("pncp/arquivos", { controle }));
  const arquivos = r.dados?.dados ?? [];
  if (r.erro || (r.carregando && !r.dados)) return null;
  if (!arquivos.length) return null;
  return (
    <div className="mb-3 flex flex-wrap items-center gap-2">
      <span className="kicker">documentos</span>
      {arquivos.map((a, i) => (
        <a
          key={i}
          href={a.url}
          target="_blank"
          rel="noreferrer"
          className="num rounded-md border border-accent px-3 py-1 text-xs uppercase tracking-wider text-accent transition-colors hover:bg-accent hover:text-surface"
        >
          {a.titulo} (PDF) →
        </a>
      ))}
    </div>
  );
}

// os itens de uma contratação; monta quando a linha abre, aí busca
function ItensDaCompra({ controle }: { controle: string }) {
  const r = useBalcao<NormalizedResponse<ItemCompra>>(caminho("pncp/itens", { controle }));
  const [vencedorDe, setVencedorDe] = useState<number | null>(null);
  const itens = r.dados?.dados ?? [];

  if (r.erro) return <ErroBox erro={r.erro} aoTentar={r.recarregar} />;
  if (r.carregando && !r.dados) return <Esqueleto linhas={3} />;
  if (!itens.length) return <Vazio>a fonte ainda não publicou os itens dessa contratação.</Vazio>;

  return (
    <ol className="flex flex-col divide-y divide-line/60">
      {itens.map((i) => (
        <li key={i.numero} className="py-2.5">
          <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
            <p className="min-w-0 flex-1 text-sm text-ink/90">
              <span className="num mr-2 text-xs text-muted">{i.numero}.</span>
              {i.descricao}
              {i.beneficio?.toUpperCase().includes("ME/EPP") && (
                <span className="num ml-2 rounded-full bg-accent-2/10 px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wider text-accent-2">
                  ME/EPP
                </span>
              )}
            </p>
            <span className="num shrink-0 text-sm text-accent">
              {i.valor_total ? formataBRL(i.valor_total) : "—"}
            </span>
          </div>
          <p className="num mt-1 text-xs text-muted">
            {i.quantidade != null && (
              <span>
                {i.quantidade.toLocaleString("pt-BR")}
                {i.unidade && ` ${i.unidade.toLowerCase()}`}
              </span>
            )}
            {i.valor_unitario && <span className="ml-2">· {formataBRL(i.valor_unitario)} cada</span>}
            {i.situacao && <span className="ml-2">· {i.situacao.toLowerCase()}</span>}
            {i.tem_resultado && (
              <button
                onClick={() => setVencedorDe((n) => (n === i.numero ? null : i.numero))}
                aria-expanded={vencedorDe === i.numero}
                className="ml-3 uppercase tracking-wider text-accent transition-colors hover:text-accent-2"
              >
                {vencedorDe === i.numero ? "fechar ▴" : "quem venceu?"}
              </button>
            )}
          </p>
          {vencedorDe === i.numero && (
            <div className="mt-2">
              <Vencedor controle={controle} item={i.numero} />
            </div>
          )}
        </li>
      ))}
    </ol>
  );
}

function Licitacoes() {
  const [modalidade, setModalidade] = useState<string>("pregao-eletronico");
  const [uf, setUf] = useState("");
  const [pagina, setPagina] = useState(1);
  const [aberta, setAberta] = useState<string | null>(null);

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
        <span className="num text-xs uppercase tracking-wider text-muted">
          <Termo t="pregao">pregão?</Termo> · <Termo t="dispensa">dispensa?</Termo>
        </span>
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
                <LerMais
                  texto={l.objeto}
                  limite={170}
                  className="mt-1 font-editorial text-sm leading-snug text-ink/80"
                />
                <p className="num mt-1 text-xs text-muted">
                  {l.modalidade}
                  {l.propostas_ate && (
                    <span className="ml-2 text-ok">propostas até {formataData(l.propostas_ate)}</span>
                  )}
                  <button
                    onClick={() =>
                      setAberta((a) => (a === l.numero_controle ? null : l.numero_controle))
                    }
                    aria-expanded={aberta === l.numero_controle}
                    className="ml-3 uppercase tracking-wider text-accent transition-colors hover:text-accent-2"
                  >
                    {aberta === l.numero_controle ? "fechar ▾" : "o que estão comprando ▸"}
                  </button>
                </p>
                {aberta === l.numero_controle && (
                  <div className="mt-3 border-t border-line/60 pt-3">
                    <ArquivosDaCompra controle={l.numero_controle} />
                    <ItensDaCompra controle={l.numero_controle} />
                  </div>
                )}
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
                <LerMais
                  texto={c.objeto}
                  limite={170}
                  className="mt-1 font-editorial text-sm leading-snug text-ink/80"
                />
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
        referencia="últimos 7 dias"
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
