"use client";

import { useState } from "react";

// amostra ilustrativa só pra mostrar como um filtro molda a resposta —
// não é uma chamada real (por isso vem rotulada como amostra).
const AMOSTRA = [
  { nome: "Ana Ribeiro", partido: "PSB", uf: "SP" },
  { nome: "Carlos Tavares", partido: "PL", uf: "SP" },
  { nome: "Helena Marques", partido: "PSB", uf: "RJ" },
  { nome: "Rafael Nunes", partido: "PT", uf: "MG" },
  { nome: "Beatriz Lima", partido: "PSB", uf: "SP" },
  { nome: "Joaquim Serra", partido: "PP", uf: "RS" },
];

export function Configurador() {
  const [uf, setUf] = useState(true);
  const [partido, setPartido] = useState(false);

  const filtrada = AMOSTRA.filter(
    (d) => (!uf || d.uf === "SP") && (!partido || d.partido === "PSB"),
  );
  const params = [uf ? "uf=SP" : null, partido ? "partido=PSB" : null].filter(Boolean);
  const query = params.length ? `?${params.join("&")}` : "";

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_1fr]">
      <div>
        <p className="mb-3 text-sm leading-relaxed text-ink/75">
          Você não baixa o banco inteiro: liga os filtros que importam e a API
          devolve só o recorte. Os mesmos nomes valem em qualquer fonte.
        </p>
        <div className="flex flex-wrap gap-2">
          <Chip ativo={uf} aoClicar={() => setUf((v) => !v)}>
            uf=SP
          </Chip>
          <Chip ativo={partido} aoClicar={() => setPartido((v) => !v)}>
            partido=PSB
          </Chip>
        </div>

        {/* a chamada montada, com os parâmetros acesos em destaque */}
        <div className="num mt-4 overflow-x-auto rounded-md border border-line bg-surface px-3 py-2.5 text-sm">
          <span className="text-muted">GET </span>
          <span className="text-ink">/v1/camara/deputados</span>
          <span className="text-accent">{query}</span>
        </div>
      </div>

      {/* o envelope que volta, encolhendo conforme os filtros */}
      <div className="rounded-md border border-line bg-ink/3 p-4">
        <div className="kicker mb-2 flex items-center justify-between">
          <span>resposta</span>
          <span className="text-accent-2">
            {filtrada.length} de {AMOSTRA.length} · amostra
          </span>
        </div>
        <pre className="num overflow-x-auto text-[0.78rem] leading-relaxed text-ink/85">
          {`{
  "fonte": "camara",
  "total": ${filtrada.length},
  "dados": [`}
          {filtrada.length === 0 && <span className="text-muted">]</span>}
          {filtrada.map((d, i) => (
            <span key={d.nome} className="imprime block">
              {`    { "nome": "${d.nome}", "partido": "${d.partido}", "uf": "${d.uf}" }`}
              {i < filtrada.length - 1 ? "," : ""}
            </span>
          ))}
          {filtrada.length > 0 && "  ]\n}"}
        </pre>
      </div>
    </div>
  );
}

function Chip({
  ativo,
  aoClicar,
  children,
}: {
  ativo: boolean;
  aoClicar: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={aoClicar}
      aria-pressed={ativo}
      className={`num rounded-md border px-3 py-1.5 text-sm transition-colors ${
        ativo
          ? "border-accent/40 bg-accent/10 text-accent"
          : "border-line bg-surface text-muted hover:text-ink"
      }`}
    >
      {children}
    </button>
  );
}
