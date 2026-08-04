"use client";

import { useContagem } from "@/hooks/useContagem";
import { useBalcao } from "@/hooks/useBalcao";
import { caminho } from "@/lib/api";
import { AzulejoGlifo } from "@/components/Azulejo";
import type { FontesOut } from "@/lib/types";

type Tom = "ink" | "accent" | "accent-2";

// números reais, conferidos nas APIs ao vivo (Câmara, IBGE, Senado, CNES).
// são estáveis o bastante pra ficarem aqui, só a contagem de fontes vem
// viva do próprio gateway, pra nunca mentir quando plugarmos uma nova.
const ACERVO: { valor: number; sufixo?: string; rotulo: string; fonte: string; tom: Tom }[] = [
  { valor: 350000, sufixo: "+", rotulo: "estabelecimentos de saúde", fonte: "SUS · CNES", tom: "accent-2" },
  { valor: 5571, rotulo: "municípios", fonte: "IBGE", tom: "ink" },
  { valor: 513, rotulo: "deputados federais", fonte: "Câmara", tom: "accent" },
  { valor: 81, rotulo: "senadores", fonte: "Senado", tom: "ink" },
  { valor: 27, rotulo: "estados: receita, imposto e gasto", fonte: "Tesouro", tom: "accent-2" },
];

function corDe(tom: Tom): string {
  return tom === "accent" ? "text-accent" : tom === "accent-2" ? "text-accent-2" : "text-ink";
}

function NumeroAcervo({ valor, sufixo, rotulo, fonte, tom }: (typeof ACERVO)[number]) {
  const n = useContagem(valor, 1100);
  return (
    <div className="flex flex-col bg-bg p-4 sm:p-5">
      <span
        className={`font-display text-3xl font-semibold leading-none tracking-tight sm:text-4xl md:text-[2.7rem] ${corDe(tom)}`}
      >
        {Math.round(n).toLocaleString("pt-BR")}
        {sufixo && <span className="align-top text-2xl">{sufixo}</span>}
      </span>
      <span className="mt-2 text-sm leading-snug text-ink/80">{rotulo}</span>
      <span className="kicker mt-1.5">{fonte}</span>
    </div>
  );
}

export function Escala() {
  // a contagem de fontes vem do /v1/fontes de verdade; 25 é só o chão
  // enquanto carrega
  const fontes = useBalcao<FontesOut>(caminho("fontes"));
  const totalFontes = fontes.dados?.total ?? 25;
  return (
    <section className="mt-14">
      <p className="kicker mb-3 flex items-center gap-2">
        <AzulejoGlifo size={14} className="text-accent-2/60" />
        O acervo, pelos números
      </p>
      <h2 className="compor font-display text-3xl font-semibold leading-[1.08] tracking-tight text-ink sm:text-4xl">
        <span className="italic text-accent">Milhões</span> de registros públicos,
        uma porta só.
      </h2>
      <p className="mt-4 max-w-[60ch] font-editorial text-[1.05rem] leading-relaxed text-ink/80">
        Vinte e cinco fontes oficiais, do Congresso ao satélite do INPE, cada
        uma com seu jeito de responder, atrás de um endereço único e do mesmo
        formato. De gastos de parlamentar a hospitais do SUS e ao preço da
        gasolina no seu estado.
      </p>

      <div className="mt-7 grid grid-cols-1 gap-px overflow-hidden rounded-lg border border-line bg-line sm:grid-cols-2 md:grid-cols-3">
        {ACERVO.map((item) => (
          <NumeroAcervo key={item.rotulo} {...item} />
        ))}
        <NumeroAcervo
          valor={totalFontes}
          rotulo="fontes oficiais, um só formato"
          fonte="Balcão · ao vivo"
          tom="accent"
        />
      </div>
    </section>
  );
}
