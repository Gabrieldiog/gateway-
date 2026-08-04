import Link from "next/link";
import { CadernoHeader } from "@/components/Caderno";
import { AzulejoGlifo } from "@/components/Azulejo";
import { TEMAS_ENDPOINTS, type Endpoint } from "@/lib/endpoints";

// base pública da API: os links abrem o JSON de verdade. Local aponta pro uvicorn;
// em produção, BALCAO_PUBLIC_URL aponta pro domínio publicado.
const BASE = process.env.BALCAO_PUBLIC_URL || "https://balcao-api.onrender.com";

// uma rota: link clicável (caminho em tinta, query em destaque) + o que devolve.
// Rotas com {placeholder} não abrem sozinhas, mostram o padrão, sem link.
function Rota({ ep }: { ep: Endpoint }) {
  const [caminho, query] = ep.path.split("?");
  return (
    <li className="flex flex-col gap-0.5 rounded-md px-2.5 py-2 hover:bg-ink/5 sm:flex-row sm:items-baseline sm:gap-4">
      {ep.pattern ? (
        <span className="num shrink-0 text-sm text-muted/70">{ep.path}</span>
      ) : (
        <a
          href={`${BASE}${ep.path}`}
          target="_blank"
          rel="noopener noreferrer"
          className="num shrink-0 break-all text-sm text-accent hover:underline"
        >
          <span className="text-ink">{caminho}</span>
          {query && <span className="text-accent">?{query}</span>}
        </a>
      )}
      <span className="text-xs leading-snug text-muted sm:ml-auto sm:text-right">{ep.desc}</span>
    </li>
  );
}

export default function CadernoEndpoints() {
  const totalFontes = TEMAS_ENDPOINTS.reduce((n, t) => n + t.fontes.length, 0);
  const totalRotas = TEMAS_ENDPOINTS.reduce(
    (n, t) => n + t.fontes.reduce((m, f) => m + f.eps.length, 0),
    0,
  );

  return (
    <div>
      <CadernoHeader
        numero="XL"
        kicker="Desenvolvedores"
        titulo="Índice de Endpoints"
        resumo="Todas as chamadas do Balcão, agrupadas por tema. Cada rota abaixo é clicável e responde JSON de verdade; os exemplos já vêm com filtros de brinde (UF, ano, termo). Sem chave na maioria, sem SDK: é só abrir o link."
      />

      {/* base + atalhos vivos */}
      <section className="mb-5 rounded-lg border border-line bg-surface p-5">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <span className="kicker text-muted">Base</span>
          <code className="num text-sm text-ink">{BASE}</code>
          <span className="text-line">·</span>
          <a href={`${BASE}/v1/fontes`} target="_blank" rel="noopener noreferrer" className="num text-sm text-accent hover:underline">
            /v1/fontes
          </a>
          <span className="text-xs text-muted">o índice sempre-atual</span>
          <span className="text-line">·</span>
          <a href={`${BASE}/scalar`} target="_blank" rel="noopener noreferrer" className="num text-sm text-accent hover:underline">
            /scalar
          </a>
          <span className="text-xs text-muted">a doc interativa</span>
        </div>
        <p className="mt-3 text-sm text-muted">
          <strong className="text-ink">{totalFontes}</strong> fontes ·{" "}
          <strong className="text-ink">{totalRotas}</strong> rotas. Filtro errado? A própria API responde{" "}
          <span className="num text-accent">400</span> com a lista dos aceitos. As marcadas{" "}
          <span className="num rounded-sm border border-ocre/60 px-1 text-[0.7rem] uppercase tracking-wider text-ocre">chave</span>{" "}
          dependem de um token grátis no servidor.
        </p>
      </section>

      {/* atalhos por tema */}
      <nav className="mb-2 flex flex-wrap gap-2 border-b border-line pb-4">
        {TEMAS_ENDPOINTS.map((t) => (
          <a
            key={t.id}
            href={`#${t.id}`}
            className="num rounded-full border border-line px-3 py-1 text-xs text-muted transition-colors hover:border-accent hover:text-accent"
          >
            <span className="text-accent" aria-hidden="true">{t.glifo}</span> {t.nome}
          </a>
        ))}
      </nav>

      {TEMAS_ENDPOINTS.map((tema) => {
        const rotas = tema.fontes.reduce((m, f) => m + f.eps.length, 0);
        return (
          <section key={tema.id} id={tema.id} className="scroll-mt-24 border-t border-line py-7 first:border-t-0">
            <div className="mb-1 flex items-baseline gap-3">
              <span className="font-display text-2xl leading-none text-accent" aria-hidden="true">
                {tema.glifo}
              </span>
              <h2 className="font-display text-2xl font-semibold tracking-tight text-ink">{tema.nome}</h2>
              <span className="num ml-auto text-xs text-muted/70">
                {tema.fontes.length} fontes · {rotas} rotas
              </span>
            </div>

            {tema.fontes.map((f) => (
              <div key={f.nome} className="border-t border-line py-4 first:mt-2">
                <div className="mb-2 flex flex-wrap items-baseline gap-x-3 gap-y-1 pl-0.5">
                  <span className="num text-sm font-bold text-ink">{f.nome}</span>
                  {f.chave && (
                    <span className="num rounded-sm border border-ocre/60 px-1.5 py-0.5 text-[0.6rem] uppercase tracking-wider text-ocre">
                      chave
                    </span>
                  )}
                  <span className="text-sm text-muted">{f.desc}</span>
                </div>
                <ul className="flex flex-col gap-0.5">
                  {f.eps.map((ep) => (
                    <Rota key={ep.path} ep={ep} />
                  ))}
                </ul>
              </div>
            ))}
          </section>
        );
      })}

      <section className="mt-6 flex items-center gap-2 rounded-lg border border-line bg-surface p-5">
        <AzulejoGlifo size={14} className="text-accent-2/60" />
        <p className="font-editorial text-sm leading-relaxed text-ink/80">
          Quer o passo a passo de como montar cada chamada, ler o envelope e tratar erro? O{" "}
          <Link href="/docs" className="text-accent hover:underline">
            Manual da API
          </Link>{" "}
          explica, e traz um prompt pronto pra uma IA explorar o Balcão por você.
        </p>
      </section>
    </div>
  );
}
