import { CadernoHeader } from "@/components/Caderno";
import { AzulejoGlifo } from "@/components/Azulejo";

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
        numero="IX"
        kicker="Manual"
        titulo="Como chamar o Balcão"
        resumo="Uma URL para cada coisa, todas no mesmo formato. Você escolhe a fonte, filtra com nomes nossos e o gateway traduz para o jeito de cada órgão. Sem chave, sem SDK — só HTTP."
      />

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
    </div>
  );
}
