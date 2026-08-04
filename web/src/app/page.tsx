import Link from "next/link";
import { AgoraBrasil } from "@/components/AgoraBrasil";
import { BuscaUnificada } from "@/components/BuscaUnificada";
import { Escala } from "@/components/Escala";
import { TEMAS } from "@/lib/cadernos";
import { AzulejoGlifo } from "@/components/Azulejo";

// a capa fala com o leitor: o que é este jornal, o que ele vai encontrar e
// como ler. A conversa de desenvolvedor mora no Manual da API.
export default function Capa() {
  return (
    <div>
      <p className="kicker mb-3">Edição diária · dados abertos do Brasil</p>
      <h1 className="compor max-w-[18ch] font-display text-3xl font-semibold leading-[1.02] tracking-tight text-ink sm:text-5xl md:text-6xl">
        O balcão único dos{" "}
        <span className="italic text-accent">dados públicos</span> brasileiros.
      </h1>
      <p className="mt-5 max-w-[64ch] font-editorial text-lg leading-relaxed text-ink/80">
        Isto é um jornal de dados. Cada caderno pega os números oficiais do
        governo, da Câmara ao Banco Central, do satélite do INPE ao posto de
        gasolina da ANP, e mostra do jeito que vieram: quanto custa, quem
        votou, o que subiu. Sem opinião no meio; todo número diz de onde veio
        e quando foi atualizado.
      </p>

      <div className="my-7">
        <AgoraBrasil />
      </div>

      <section className="mt-12">
        <p className="kicker mb-3 flex items-center gap-2">
          <AzulejoGlifo size={14} className="text-accent-2/60" />
          Comece perguntando
        </p>
        <p className="mb-4 max-w-[62ch] font-editorial text-[1.05rem] leading-relaxed text-ink/80">
          Digite um nome, uma cidade, um tema; a busca dispara em várias
          fontes ao mesmo tempo e os resultados <em>imprimem</em> aqui conforme
          cada órgão responde.
        </p>
        <BuscaUnificada />
      </section>

      <section className="mt-14">
        <p className="kicker mb-4 flex items-center gap-2">
          <AzulejoGlifo size={14} className="text-accent-2/60" />
          O que você vai encontrar
        </p>
        <div className="flex flex-col gap-4">
          {TEMAS.map((g) => (
            <div
              key={g.nome}
              className="overflow-hidden rounded-lg border border-line bg-surface"
            >
              <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1 border-b border-line px-5 pb-3 pt-4">
                <h2 className="font-display text-2xl font-semibold tracking-tight text-ink">
                  {g.nome}
                </h2>
                {g.desc && (
                  <p className="max-w-[58ch] font-editorial text-sm leading-relaxed text-ink/70">
                    {g.desc}
                  </p>
                )}
              </div>
              <div className="grid grid-cols-1 gap-px bg-line sm:grid-cols-2 lg:grid-cols-3">
                {g.cadernos.map((c, i) => (
                  <Link
                    key={c.href}
                    href={c.href}
                    className="imprime group flex items-baseline gap-3 bg-surface p-4 transition-colors hover:bg-surface-2"
                    style={{ animationDelay: `${i * 60}ms` }}
                  >
                    <span className="num shrink-0 text-sm text-accent">{c.num}</span>
                    <span className="min-w-0">
                      <span className="block truncate font-display text-lg text-ink group-hover:text-accent">
                        {c.nome}
                      </span>
                      <span className="block text-[0.82rem] leading-snug text-muted">
                        {c.sub}
                      </span>
                    </span>
                    <span className="num ml-auto self-center text-muted transition-transform group-hover:translate-x-1">
                      →
                    </span>
                  </Link>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="mt-14">
        <p className="kicker mb-4 flex items-center gap-2">
          <AzulejoGlifo size={14} className="text-accent-2/60" />
          Como ler este jornal
        </p>
        <div className="grid grid-cols-1 gap-px overflow-hidden rounded-lg border border-line bg-line sm:grid-cols-3">
          <ComoLer titulo="Cada número tem selo">
            Um selo em cada caderno diz o ritmo do dado: <em>ao vivo</em> com o
            relógio contando, diário, semanal ou mensal; no ritmo em que o
            órgão publica, sem fingir tempo real onde não há.
          </ComoLer>
          <ComoLer titulo="Toda fonte tem link">
            No pé de cada caderno está o órgão de onde os números saíram, com
            link pra fonte oficial. Não acredite na gente: confira.
          </ComoLer>
          <ComoLer titulo="Quando a fonte cai, a gente avisa">
            API de governo cai. Quando acontece, o Balcão mostra o último dado
            que guardou, carimbado com a hora, ou avisa com todas as letras,
            em vez de inventar número.
          </ComoLer>
        </div>
      </section>

      <Escala />

      <div className="regua-dupla desenha-regua my-10" />

      <section className="flex flex-wrap items-baseline gap-x-8 gap-y-3 pb-4">
        <Link href="/sobre" className="group">
          <span className="font-display text-lg text-ink group-hover:text-accent">
            Sobre o Balcão
          </span>
          <span className="ml-2 text-sm text-muted">o que é este projeto →</span>
        </Link>
        <Link href="/fontes" className="group">
          <span className="font-display text-lg text-ink group-hover:text-accent">
            Expediente
          </span>
          <span className="ml-2 text-sm text-muted">todas as fontes oficiais →</span>
        </Link>
        <Link href="/docs" className="group">
          <span className="font-display text-lg text-ink group-hover:text-accent">
            É desenvolvedor?
          </span>
          <span className="ml-2 text-sm text-muted">tudo aqui também é API →</span>
        </Link>
      </section>
    </div>
  );
}

function ComoLer({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <div className="bg-bg p-5">
      <h3 className="mb-2 font-display text-lg font-semibold text-ink">{titulo}</h3>
      <p className="font-editorial text-[0.95rem] leading-relaxed text-ink/75">{children}</p>
    </div>
  );
}
