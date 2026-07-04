import { CadernoHeader } from "@/components/Caderno";
import { AzulejoGlifo } from "@/components/Azulejo";
import { Configurador } from "@/components/Configurador";
import { PromptIA } from "@/components/PromptIA";

// uma linha de exemplo: curl + url com o path em tinta e a query em destaque
function Linha({ nota, url }: { nota?: string; url: string }) {
  const [caminho, query] = url.split("?");
  return (
    <div className="num overflow-x-auto whitespace-nowrap rounded-md border border-line bg-surface px-3 py-2.5 text-sm">
      {nota && <div className="mb-1 whitespace-normal text-xs text-muted">› {nota}</div>}
      <span className="text-muted">curl &quot;localhost:8000</span>
      <span className="text-ink">{caminho}</span>
      {query && <span className="text-accent">?{query}</span>}
      <span className="text-muted">&quot;</span>
    </div>
  );
}

function Secao({
  numero,
  titulo,
  children,
  exemplos,
}: {
  numero: string;
  titulo: string;
  children: React.ReactNode;
  exemplos: { nota?: string; url: string }[];
}) {
  return (
    <section className="border-t border-line py-7 first:border-t-0">
      <p className="kicker mb-2 flex items-center gap-2">
        <span className="num text-accent">{numero}</span>
        <span>{titulo}</span>
      </p>
      <p className="mb-4 max-w-[64ch] font-editorial text-[1.02rem] leading-relaxed text-ink/80">
        {children}
      </p>
      <div className="flex flex-col gap-2">
        {exemplos.map((e) => (
          <Linha key={e.url} nota={e.nota} url={e.url} />
        ))}
      </div>
    </section>
  );
}

export default function CadernoDocs() {
  return (
    <div>
      <CadernoHeader
        numero="XXV"
        kicker="Desenvolvedores"
        titulo="Como chamar o Balcão"
        resumo="Tudo que o jornal mostra sai desta API — e ela é sua também. Uma URL para cada coisa, todas no mesmo formato: você escolhe a fonte, filtra com nomes nossos e o gateway traduz para o jeito de cada órgão. Sem chave, sem SDK — só HTTP."
      />

      <section className="mb-6 rounded-lg border border-accent/30 bg-accent/5 p-6">
        <p className="kicker mb-3 flex items-center gap-2 text-accent">
          <AzulejoGlifo size={14} className="text-accent/60" />
          Comece em 30 segundos
        </p>
        <ol className="flex flex-col gap-2.5 font-editorial text-[1.02rem] leading-relaxed text-ink/85">
          <li>
            <span className="num mr-2 text-accent">1.</span>
            Pergunte à API o que ela sabe fazer:{" "}
            <code className="num text-sm text-accent">curl localhost:8000/v1/fontes</code> — vêm
            as 25 fontes, cada uma com seus recursos e filtros.
          </li>
          <li>
            <span className="num mr-2 text-accent">2.</span>
            Chame um recurso:{" "}
            <code className="num text-sm text-accent break-all">curl &quot;localhost:8000/v1/bacen/selic?ultimos=5&quot;</code>
            . Sem chave, sem cadastro, sem SDK.
          </li>
          <li>
            <span className="num mr-2 text-accent">3.</span>
            Leia o envelope: <code className="num text-sm">dados</code> é sempre uma lista
            normalizada, <code className="num text-sm">meta</code> conta a história (cache,
            paginação, fonte oficial). Só isso.
          </li>
        </ol>
      </section>

      <section className="mb-2 rounded-lg border border-line bg-surface p-6">
        <p className="kicker mb-4 flex items-center gap-2">
          <AzulejoGlifo size={14} className="text-accent-2/60" />
          Você configura, a API entrega
        </p>
        <Configurador />
      </section>

      <Secao
        numero="01"
        titulo="Direto por fonte"
        exemplos={[
          { nota: "deputados de SP no PL", url: "localhost:8000/v1/camara/deputados?uf=SP&partido=PL" },
          { nota: "a cota parlamentar de um deputado num ano", url: "localhost:8000/v1/camara/deputados/204528/despesas?ano=2025" },
          { nota: "como cada deputado votou (votação nominal)", url: "localhost:8000/v1/camara/votacoes/2629954-8/votos" },
          { nota: "hospitais gerais de SP (tipo é o código CNES)", url: "localhost:8000/v1/sus/estabelecimentos?uf=SP&tipo=5" },
          { nota: "receita, imposto e gasto de um estado", url: "localhost:8000/v1/tesouro/estados/SP" },
          { nota: "Selic dos últimos 10 pontos", url: "localhost:8000/v1/bacen/selic?ultimos=10" },
        ]}
      >
        O formato é <code className="num text-accent">/v1/&#123;fonte&#125;/&#123;recurso&#125;</code>.
        Os filtros têm nomes nossos (<code className="num">uf</code>,{" "}
        <code className="num">partido</code>, <code className="num">ano</code>) e
        o conector traduz para o que cada API espera. Filtro errado responde 400
        com a lista dos aceitos.
      </Secao>

      <Secao
        numero="02"
        titulo="Busca unificada"
        exemplos={[
          { nota: "dispara nas fontes escolhidas, em paralelo", url: "localhost:8000/v1/buscar?q=silva&fontes=camara,senado" },
          { nota: "sem fontes= busca em todas", url: "localhost:8000/v1/buscar?q=campinas" },
        ]}
      >
        Uma chamada, várias fontes ao mesmo tempo. O <code className="num">fontes=</code>{" "}
        escolhe onde procurar; se uma fonte cair, as outras ainda respondem, e o
        erro isolado aparece no <code className="num">meta</code>.
      </Secao>

      <Secao
        numero="03"
        titulo="Recurso cross-fonte"
        exemplos={[
          { nota: "resolve o parlamentar por id ou nome e agrega o gasto", url: "localhost:8000/v1/gastos?deputado=Adriana&uf=SP&ano=2025" },
        ]}
      >
        Aqui você pede o <em>dado</em>, não a fonte. O Balcão decide onde buscar,
        resolve a pessoa por id ou nome e devolve o total já somado por tipo de
        despesa.
      </Secao>

      <Secao
        numero="04"
        titulo="Descoberta"
        exemplos={[
          { nota: "lista conectores, recursos e filtros de cada um", url: "localhost:8000/v1/fontes" },
          { nota: "Swagger interativo, a API se autodescreve", url: "localhost:8000/docs" },
        ]}
      >
        A própria API conta o que sabe fazer. <code className="num">/v1/fontes</code>{" "}
        devolve cada conector com seus recursos e filtros; o{" "}
        <code className="num">/docs</code> abre o Swagger.
      </Secao>

      <section className="mt-4 rounded-lg border border-line bg-surface p-6">
        <p className="kicker mb-3 flex items-center gap-2">
          <AzulejoGlifo size={14} className="text-accent-2/60" />
          A resposta, sempre no mesmo envelope
        </p>
        <pre className="num overflow-x-auto rounded-md bg-ink/3 p-4 text-[0.8rem] leading-relaxed text-ink/85">
{`{
  "fonte": "camara",
  "recurso": "deputados",
  "dados": [ { "id": 204528, "nome": "Adriana Ventura", "partido": "NOVO", "uf": "SP" } ],
  "total": 1,
  "meta": { "pagina": 1, "tem_proxima": true, "cache": "hit" }
}`}
        </pre>
        <ul className="mt-4 flex flex-col gap-2 font-editorial text-[1.0rem] leading-relaxed text-ink/80">
          <li>
            <code className="num text-accent">dados</code> — sempre uma lista, já
            normalizada (datas em ISO, CNPJ só dígitos, UF padronizada).
          </li>
          <li>
            <code className="num text-accent">meta.cache</code> —{" "}
            <span className="text-ok">hit</span> (veio do cache),{" "}
            <span className="text-accent-2">miss</span> (foi à fonte) ou{" "}
            <span className="text-ocre">stale</span> (a fonte caiu e o Balcão
            serviu o dado recente com aviso).
          </li>
          <li>
            <code className="num text-accent">meta.descartados</code> — quantos
            registros podres foram filtrados sem derrubar o lote.
          </li>
        </ul>
      </section>

      <section className="mt-6 rounded-lg border border-line bg-surface p-6">
        <p className="kicker mb-3 flex items-center gap-2">
          <AzulejoGlifo size={14} className="text-accent-2/60" />
          Quando algo dá errado
        </p>
        <p className="mb-4 max-w-[64ch] font-editorial text-[1.02rem] leading-relaxed text-ink/80">
          Todo erro volta como JSON com a chave <code className="num text-sm">erro</code> em
          português e, quando faz sentido, um <code className="num text-sm">detalhes</code> com o
          caminho da correção. Os códigos:
        </p>
        <div className="flex flex-col gap-2">
          <Erro codigo="400" nome="filtro inválido">
            você mandou um parâmetro que o recurso não aceita — a resposta lista os aceitos.
            Corrija e repita.
          </Erro>
          <Erro codigo="404" nome="não existe">
            fonte, recurso ou dado inexistente — inclusive quando o órgão ainda não publicou o
            arquivo daquele dia.
          </Erro>
          <Erro codigo="429" nome="calma">
            passou de 100 chamadas por minuto. Espere alguns segundos; para varreduras, use o
            cache a seu favor (chamadas idênticas nem contam contra a fonte).
          </Erro>
          <Erro codigo="502" nome="fonte fora do ar">
            a API do órgão caiu — comum e passageiro. O gateway já tentou 3 vezes com backoff;
            se tiver cópia recente, responde 200 com <code className="num text-xs">meta.cache: &quot;stale&quot;</code>.
            Tente de novo em instantes.
          </Erro>
          <Erro codigo="503" nome="falta chave">
            essa fonte exige chave de API (grátis) que não está configurada no servidor —
            veja o <code className="num text-xs">.env.example</code> do repositório.
          </Erro>
        </div>
        <p className="mt-4 border-t border-line pt-3 font-editorial text-sm italic text-muted">
          Tudo é GET e idempotente: repetir uma chamada nunca muda nada. TTL do cache: 10
          minutos (dados ao vivo não são cacheados).
        </p>
      </section>

      <section className="mt-6">
        <p className="kicker mb-2 flex items-center gap-2">
          <AzulejoGlifo size={14} className="text-accent-2/60" />
          Quer uma ajudinha nossa?
        </p>
        <p className="mb-4 max-w-[64ch] font-editorial text-[1.05rem] leading-relaxed text-ink/80">
          Se você for usar uma IA (Claude, ChatGPT, Gemini…) pra explorar o Balcão, não
          precisa explicar nada pra ela: copie o prompt abaixo e cole na conversa. Ele ensina a
          API inteira e — a parte boa — instrui a IA a <em>narrar o que está fazendo</em> a
          cada passo: o que vai buscar, o que veio, e o que aconteceu quando der erro. Você
          nunca fica no escuro.
        </p>
        <PromptIA />
      </section>
    </div>
  );
}

function Erro({
  codigo,
  nome,
  children,
}: {
  codigo: string;
  nome: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-baseline gap-3 rounded-md border border-line bg-bg px-4 py-2.5">
      <span className="num shrink-0 text-sm font-semibold text-accent">{codigo}</span>
      <span className="num shrink-0 text-xs uppercase tracking-wider text-muted">{nome}</span>
      <span className="min-w-0 text-sm leading-relaxed text-ink/80">{children}</span>
    </div>
  );
}
