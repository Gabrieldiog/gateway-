import Link from "next/link";
import { BuscaUnificada } from "@/components/BuscaUnificada";
import { CADERNOS } from "@/lib/cadernos";
import { AzulejoGlifo } from "@/components/Azulejo";

export default function Capa() {
  const outros = CADERNOS.filter((c) => c.href !== "/");

  return (
    <div>
      <p className="kicker mb-3">Edição diária · dados abertos do Brasil</p>
      <h1 className="compor max-w-[18ch] font-display text-5xl font-semibold leading-[1.02] tracking-tight text-ink sm:text-6xl">
        O balcão único dos{" "}
        <span className="italic text-accent">dados públicos</span> brasileiros.
      </h1>
      <p className="mt-5 max-w-[64ch] font-editorial text-lg leading-relaxed text-ink/80">
        Uma porta só para a Câmara, o Senado, o Banco Central e o IBGE — tudo
        normalizado no mesmo formato, com cache e resiliência. Faça uma busca: as
        fontes respondem em paralelo e <em>imprimem</em> aqui conforme chegam, com
        a latência de cada uma e o estado do cache à mostra.
      </p>

      <div className="regua-dupla desenha-regua my-7" />

      <BuscaUnificada />

      <section className="mt-14">
        <p className="kicker mb-4 flex items-center gap-2">
          <AzulejoGlifo size={14} className="text-accent-2/60" />
          Nos cadernos de hoje
        </p>
        <div className="grid grid-cols-1 gap-px overflow-hidden rounded-lg border border-line bg-line sm:grid-cols-2">
          {outros.map((c) => (
            <Link
              key={c.href}
              href={c.href}
              className="group flex items-baseline gap-3 bg-surface p-5 transition-colors hover:bg-surface-2"
            >
              <span className="num shrink-0 text-sm text-accent">{c.num}</span>
              <span>
                <span className="block font-display text-xl text-ink group-hover:text-accent">
                  {c.nome}
                </span>
                <span className="text-sm text-muted">{c.sub}</span>
              </span>
              <span className="num ml-auto self-center text-muted transition-transform group-hover:translate-x-1">
                →
              </span>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
