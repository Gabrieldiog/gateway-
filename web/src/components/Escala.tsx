"use client";

import { useState } from "react";
import { useContagem } from "@/hooks/useContagem";
import { AzulejoGlifo } from "@/components/Azulejo";

type Tom = "ink" | "accent" | "accent-2";

// números reais, conferidos nas APIs ao vivo (Câmara, IBGE, Senado, CNES).
// são estáveis o bastante pra ficarem aqui em vez de uma chamada por carga.
const ACERVO: { valor: number; sufixo?: string; rotulo: string; fonte: string; tom: Tom }[] = [
  { valor: 350000, sufixo: "+", rotulo: "estabelecimentos de saúde", fonte: "SUS · CNES", tom: "accent-2" },
  { valor: 5571, rotulo: "municípios", fonte: "IBGE", tom: "ink" },
  { valor: 513, rotulo: "deputados federais", fonte: "Câmara", tom: "accent" },
  { valor: 81, rotulo: "senadores", fonte: "Senado", tom: "ink" },
  { valor: 27, rotulo: "estados: receita, imposto e gasto", fonte: "Tesouro", tom: "accent-2" },
  { valor: 6, rotulo: "fontes oficiais, um só formato", fonte: "Balcão", tom: "accent" },
];

function corDe(tom: Tom): string {
  return tom === "accent" ? "text-accent" : tom === "accent-2" ? "text-accent-2" : "text-ink";
}

function NumeroAcervo({ valor, sufixo, rotulo, fonte, tom }: (typeof ACERVO)[number]) {
  const n = useContagem(valor, 1100);
  return (
    <div className="flex flex-col bg-bg p-5">
      <span
        className={`font-display text-4xl font-semibold leading-none tracking-tight sm:text-[2.7rem] ${corDe(tom)}`}
      >
        {Math.round(n).toLocaleString("pt-BR")}
        {sufixo && <span className="align-top text-2xl">{sufixo}</span>}
      </span>
      <span className="mt-2 text-sm leading-snug text-ink/80">{rotulo}</span>
      <span className="kicker mt-1.5">{fonte}</span>
    </div>
  );
}

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

function Configurador() {
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
      <div className="rounded-md border border-line bg-ink/[0.03] p-4">
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

export function Escala() {
  return (
    <section className="mt-16">
      <p className="kicker mb-3 flex items-center gap-2">
        <AzulejoGlifo size={14} className="text-accent-2/60" />
        O acervo, por os números
      </p>
      <h2 className="compor font-display text-3xl font-semibold leading-[1.08] tracking-tight text-ink sm:text-4xl">
        <span className="italic text-accent">Milhões</span> de registros públicos —
        uma porta só.
      </h2>
      <p className="mt-4 max-w-[60ch] font-editorial text-[1.05rem] leading-relaxed text-ink/80">
        Seis órgãos federais, cada um com seu jeito de responder, atrás de um
        endereço único e do mesmo schema. De gastos de parlamentar a hospitais
        do SUS e às contas dos estados.
      </p>

      <div className="mt-7 grid grid-cols-2 gap-px overflow-hidden rounded-lg border border-line bg-line sm:grid-cols-3">
        {ACERVO.map((item) => (
          <NumeroAcervo key={item.rotulo} {...item} />
        ))}
      </div>

      <div className="regua-dupla desenha-regua my-9" />

      <p className="kicker mb-4">Você configura, a API entrega</p>
      <Configurador />
    </section>
  );
}
