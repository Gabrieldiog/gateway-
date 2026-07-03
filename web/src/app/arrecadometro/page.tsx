"use client";

import { useEffect, useState } from "react";
import { CadernoHeader } from "@/components/Caderno";
import { Card } from "@/components/Card";
import { Seletor } from "@/components/Seletor";
import { Esqueleto, ErroBox, Vazio } from "@/components/Estados";
import { SeloFonte } from "@/components/SeloFonte";
import { useBalcao } from "@/hooks/useBalcao";
import { useArrecadometro } from "@/hooks/useArrecadometro";
import { caminho, escalaReais, formataReaisCompacto } from "@/lib/api";
import { ANO_ATUAL } from "@/lib/datas";
import { UFS, CAPITAIS } from "@/lib/ufs";
import type { Arrecadacao, Municipio, NormalizedResponse } from "@/lib/types";

type Nivel = "uniao" | "estado" | "municipio";
const NIVEIS: [Nivel, string][] = [
  ["uniao", "Brasil"],
  ["estado", "Estado"],
  ["municipio", "Cidade"],
];

export default function CadernoArrecadometro() {
  const [nivel, setNivel] = useState<Nivel>("uniao");
  const [uf, setUf] = useState("GO");
  const [ibge, setIbge] = useState(CAPITAIS["GO"]);
  const [metrica, setMetrica] = useState("arrecadacao"); // arrecadacao | impostos | <sigla>
  const [baseAno, setBaseAno] = useState(ANO_ATUAL);

  function escolheNivel(n: Nivel) {
    setNivel(n);
    setMetrica("arrecadacao");
    if (n === "municipio") setIbge(CAPITAIS[uf] ?? "");
  }
  function escolheUf(u: string) {
    setUf(u);
    if (nivel === "municipio") setIbge(CAPITAIS[u] ?? "");
  }

  const munis = useBalcao<NormalizedResponse<Municipio>>(
    nivel === "municipio" ? caminho("ibge/municipios", { uf }) : null,
  );
  const municipios = munis.dados?.dados ?? [];

  const ente = nivel === "uniao" ? "brasil" : nivel === "estado" ? uf : ibge;
  const arr = useBalcao<Arrecadacao>(ente ? caminho("arrecadacao", { ente, ano: baseAno }) : null);
  const fin = arr.dados?.ente ?? null;
  const impostos = arr.dados?.impostos ?? [];

  // ao trocar de ente tenta de novo o ano corrente; se as contas ainda não
  // fecharam, cai pro anterior — sem ano cravado, vira com o calendário
  useEffect(() => setBaseAno(ANO_ATUAL), [ente]);
  useEffect(() => {
    if (arr.dados && baseAno === ANO_ATUAL && !arr.dados.ente?.arrecadacao_total) {
      setBaseAno(ANO_ATUAL - 1);
    }
  }, [arr.dados, baseAno]);

  // valor anual base conforme a métrica escolhida
  let base = 0;
  let rotuloMetrica = "Arrecadação total";
  if (metrica === "impostos") {
    base = Number(fin?.receita_impostos ?? 0);
    rotuloMetrica = "Impostos";
  } else if (metrica !== "arrecadacao") {
    const imp = impostos.find((i) => i.sigla === metrica);
    base = Number(imp?.valor ?? 0);
    rotuloMetrica = imp?.nome ?? metrica;
  } else {
    base = Number(fin?.arrecadacao_total ?? 0);
  }

  const vivo = useArrecadometro(base);
  const aviso = arr.dados?.meta?.aviso as string | undefined;
  const carregandoVazio = arr.carregando && !arr.dados;

  return (
    <div>
      <CadernoHeader
        numero="XIII"
        kicker="ao vivo · estimado"
        titulo="Arrecadômetro"
        resumo={`Quanto o Brasil (ou um estado, ou uma cidade) já arrecadou em ${ANO_ATUAL}, subindo a cada instante. Igual ao painel da Associação Comercial de SP: é o valor oficial do último ano projetado no tempo — estimativa, não medição por segundo (esse dado não existe).`}
      />

      <div className="mb-6 flex flex-wrap items-center gap-x-5 gap-y-3">
        <div className="inline-flex gap-0.5 rounded-md border border-line p-0.5">
          {NIVEIS.map(([v, label]) => (
            <button
              key={v}
              onClick={() => escolheNivel(v)}
              aria-pressed={nivel === v}
              className={`num rounded px-3 py-1 text-xs uppercase tracking-wider transition-colors ${
                nivel === v ? "bg-accent/15 font-semibold text-accent" : "text-muted hover:text-ink"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {nivel !== "uniao" && (
          <label className="num flex items-center gap-2 text-xs uppercase tracking-wider text-muted">
            UF
            <Seletor value={uf} onChange={(e) => escolheUf(e.target.value)}>
              {UFS.map((u) => (
                <option key={u} value={u}>
                  {u}
                </option>
              ))}
            </Seletor>
          </label>
        )}

        {nivel === "municipio" && (
          <label className="num flex items-center gap-2 text-xs uppercase tracking-wider text-muted">
            Cidade
            <Seletor
              value={ibge}
              onChange={(e) => setIbge(e.target.value)}
              disabled={!municipios.length}
              className="max-w-56"
            >
              {municipios.length ? (
                municipios.map((m) => (
                  <option key={m.id} value={String(m.id)}>
                    {m.nome}
                  </option>
                ))
              ) : (
                <option value={ibge}>carregando…</option>
              )}
            </Seletor>
          </label>
        )}

        <label className="num flex items-center gap-2 text-xs uppercase tracking-wider text-muted">
          Contar
          <Seletor
            value={metrica}
            onChange={(e) => setMetrica(e.target.value)}
            className="max-w-64"
          >
            <option value="arrecadacao">Arrecadação total</option>
            <option value="impostos">Impostos (todos)</option>
            {impostos
              .filter((i) => i.sigla !== "OUTROS")
              .map((i) => (
                <option key={i.sigla} value={i.sigla}>
                  {i.sigla} — {i.nome}
                </option>
              ))}
          </Seletor>
        </label>
      </div>

      {arr.erro ? (
        <ErroBox erro={arr.erro} aoTentar={arr.recarregar} />
      ) : carregandoVazio ? (
        <Esqueleto linhas={3} />
      ) : fin && base > 0 ? (
        <Painel
          ente={fin.ente}
          metrica={rotuloMetrica}
          vivo={vivo}
          base={base}
          baseAno={baseAno}
        />
      ) : (
        <Vazio>{aviso ?? "sem base de arrecadação pra esse ente."}</Vazio>
      )}

      <SeloFonte fonte={arr.dados?.fonte} />
    </div>
  );
}

function Painel({
  ente,
  metrica,
  vivo,
  base,
  baseAno,
}: {
  ente: string;
  metrica: string;
  vivo: number;
  base: number;
  baseAno: number;
}) {
  const baseEsc = escalaReais(base);
  return (
    <Card className="overflow-hidden p-6 sm:p-8">
      <div className="mb-3 flex items-center gap-2">
        <span className="relative flex h-2.5 w-2.5">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent opacity-75" />
          <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-accent" />
        </span>
        <span className="num text-xs uppercase tracking-wider text-muted">
          {ente} · {metrica} · acumulado de {ANO_ATUAL}
        </span>
      </div>

      <p className="num tabular-nums break-words text-4xl font-semibold leading-tight tracking-tight text-accent sm:text-6xl">
        R$ {Math.floor(vivo).toLocaleString("pt-BR")}
      </p>

      <p className="num mt-2 text-lg text-muted">
        ≈ {formataReaisCompacto(vivo)}
      </p>

      <p className="mt-5 max-w-[64ch] border-t border-line pt-3 font-editorial text-sm italic text-muted">
        Estimativa ao vivo: o total oficial de <strong className="not-italic">{baseAno}</strong> (R${" "}
        {baseEsc.valor.toLocaleString("pt-BR", { maximumFractionDigits: 2 })} {baseEsc.unidade})
        projetado nos segundos do ano — a mesma lógica do Impostômetro. O dado é real; o movimento
        por segundo é projeção, porque arrecadação por segundo não existe em lugar nenhum.
      </p>
    </Card>
  );
}
