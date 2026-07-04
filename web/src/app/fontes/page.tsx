"use client";

import { CadernoHeader } from "@/components/Caderno";
import { Carimbo } from "@/components/Carimbo";
import { AzulejoGlifo } from "@/components/Azulejo";
import { Esqueleto, ErroBox } from "@/components/Estados";
import { useBalcao } from "@/hooks/useBalcao";
import { caminho } from "@/lib/api";
import type { FontesOut } from "@/lib/types";

export default function CadernoExpediente() {
  const { dados, carregando, erro, recarregar } = useBalcao<FontesOut>(caminho("fontes"));
  const fontes = dados?.fontes ?? [];

  return (
    <div>
      <CadernoHeader
        numero="XXVI"
        kicker="Expediente"
        titulo="As repartições do Balcão"
        resumo="Cada fonte implementa o mesmo contrato: traduz a chamada genérica para a sua API e devolve no schema normalizado. Plugar uma nova é escrever uma classe e registrá-la — esta página se monta a partir do que o gateway de fato expõe em /v1/fontes."
      />

      <div className="mb-6 grid grid-cols-1 gap-3 sm:grid-cols-3">
        <NotaTecnica titulo="Normalização" texto="Datas em ISO, CNPJ só dígitos, UF validada — o mesmo formato venha de onde vier." />
        <NotaTecnica titulo="Resiliência" texto="Retry com backoff, circuit breaker e fallback para cache stale quando a fonte cai." />
        <NotaTecnica titulo="Cache" texto="Resposta repetida sai da memória; o carimbo de cada caderno mostra hit, miss ou stale." />
      </div>

      {erro ? (
        <ErroBox erro={erro} aoTentar={recarregar} />
      ) : carregando && !dados ? (
        <Esqueleto linhas={6} />
      ) : (
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
          {fontes.map((f) => (
            <article key={f.nome} className="relative rounded-lg border border-line bg-surface p-5">
              <AzulejoGlifo size={14} className="absolute left-2 top-2 text-accent-2/35" />
              <div className="flex items-start justify-between gap-3 pl-5">
                <div className="min-w-0">
                  <h2 className="font-display text-2xl capitalize leading-tight text-ink">{f.nome}</h2>
                  <p className="num mt-0.5 break-all text-xs text-accent-2">{f.base_url}</p>
                </div>
                <span
                  className={`num shrink-0 rounded-sm border px-2 py-0.5 text-[0.62rem] uppercase tracking-wider ${
                    f.precisa_chave ? "border-ocre/60 text-ocre" : "border-ok/50 text-ok"
                  }`}
                >
                  {f.precisa_chave ? "requer chave" : "aberta"}
                </span>
              </div>
              <p className="mb-4 mt-2 pl-5 font-editorial text-sm leading-snug text-ink/80">
                {f.descricao}
              </p>
              <ul className="flex flex-col gap-1 border-t border-line pt-3">
                {Object.entries(f.recursos).map(([rec, desc]) => (
                  <li key={rec} className="flex gap-2 text-sm">
                    <span className="num shrink-0 text-accent-2">{rec}</span>
                    <span className="truncate text-muted" title={desc}>
                      {desc}
                    </span>
                  </li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      )}

      <p className="mt-8 flex items-center justify-center gap-2 text-center">
        <Carimbo fonte="BALCÃO" cache={null} ms={null} />
        <span className="num text-xs text-muted">
          gateway de dados públicos · {dados?.total ?? "—"} fontes registradas
        </span>
      </p>
    </div>
  );
}

function NotaTecnica({ titulo, texto }: { titulo: string; texto: string }) {
  return (
    <div className="rounded-lg border border-line bg-surface-2/50 p-4">
      <p className="kicker mb-1.5">{titulo}</p>
      <p className="font-editorial text-sm leading-snug text-ink/80">{texto}</p>
    </div>
  );
}
