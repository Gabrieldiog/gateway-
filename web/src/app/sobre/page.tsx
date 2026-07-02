import Link from "next/link";
import { CadernoHeader } from "@/components/Caderno";
import { AzulejoGlifo } from "@/components/Azulejo";

// a página institucional fala com o leitor: o que é o projeto, de onde vêm
// os números e o compromisso de honestidade. A conversa técnica mora no
// Manual da API.
export default function CadernoSobre() {
  return (
    <div>
      <CadernoHeader
        numero="XXIV"
        kicker="Sobre"
        titulo="O que é o Balcão"
        resumo="Um jornal de dados públicos: os números oficiais do Brasil, lidos direto da fonte e mostrados sem editorial. Esta página explica de onde vem cada dado, o caminho que ele percorre e o que prometemos a você."
      />

      <Secao titulo="Um jornal feito de números">
        <p>
          O Balcão junta <strong>25 fontes oficiais</strong> — Câmara, Senado,
          Banco Central, IBGE, Tesouro Nacional, INPE, Fiocruz, ANP, entre
          outras — atrás de uma porta só, e as apresenta em cadernos temáticos,
          como um jornal: Governo, Economia, Território, Infraestrutura e
          Social. Cada caderno responde uma pergunta concreta: quanto ganha um
          deputado, quanto está a gasolina no seu estado, quantos focos de
          queimada os satélites viram ontem.
        </p>
        <p>
          Não escrevemos opinião. O trabalho aqui é de <em>tradução</em>: órgão
          público fala em código, planilha e sigla — o Balcão devolve em número
          limpo, com contexto e fonte.
        </p>
      </Secao>

      <Secao titulo="O caminho de um número">
        <p>
          Todo dado que você vê percorreu o mesmo caminho, e nenhum trecho dele
          é manual:
        </p>
        <div className="num my-4 overflow-x-auto whitespace-nowrap rounded-md border border-line bg-surface px-4 py-3 text-sm text-ink/85">
          órgão oficial <span className="text-accent">→</span> API pública do órgão{" "}
          <span className="text-accent">→</span> gateway do Balcão (normaliza, guarda cópia,
          tenta de novo se falhar) <span className="text-accent">→</span> o caderno que você lê
        </div>
        <p>
          “Normalizar” quer dizer: datas todas no mesmo formato, CNPJ sem
          máscara, estados com a mesma sigla — porque cada repartição escreve
          de um jeito, e ler o Brasil inteiro exige um idioma só.
        </p>
      </Secao>

      <Secao titulo="O compromisso de honestidade">
        <ul className="flex list-none flex-col gap-3 p-0">
          <Compromisso titulo="Ritmo verdadeiro">
            O selo de cada caderno diz a cadência real do dado: ao vivo com o
            relógio contando, diário, semanal ou mensal. Não fingimos tempo
            real onde o órgão publica uma vez por dia.
          </Compromisso>
          <Compromisso titulo="Fonte à vista">
            Todo caderno traz no pé o órgão de origem e o link oficial. Se
            quiser conferir na fonte, o caminho está sempre aberto.
          </Compromisso>
          <Compromisso titulo="Falha declarada">
            API de governo cai — é normal e costuma voltar sozinha. Quando
            acontece, mostramos o último dado guardado com o carimbo de quando
            foi salvo, ou avisamos do erro com todas as letras. Número
            inventado, nunca.
          </Compromisso>
          <Compromisso titulo="Nada de dado pessoal">
            Só circulam aqui dados que os próprios órgãos publicam como
            abertos. O Balcão não coleta, não cadastra e não rastreia quem lê.
          </Compromisso>
        </ul>
      </Secao>

      <Secao titulo="O que o Balcão não é">
        <p>
          Não é o site oficial de nenhum órgão — para o ato administrativo que
          vale juridicamente, consulte sempre a fonte (os links estão no{" "}
          <Link href="/fontes" className="text-accent underline decoration-accent/40 underline-offset-2 hover:decoration-accent">
            Expediente
          </Link>
          ). É um projeto de engenharia de dados feito para demonstrar como as
          informações públicas do país podem ser lidas num lugar só, com
          arquitetura aberta.
        </p>
      </Secao>

      <div className="regua-dupla my-8" />

      <section className="flex flex-wrap items-baseline gap-x-8 gap-y-3">
        <Link href="/fontes" className="group">
          <span className="font-display text-lg text-ink group-hover:text-accent">Expediente</span>
          <span className="ml-2 text-sm text-muted">as 25 fontes, uma a uma →</span>
        </Link>
        <Link href="/docs" className="group">
          <span className="font-display text-lg text-ink group-hover:text-accent">Manual da API</span>
          <span className="ml-2 text-sm text-muted">tudo aqui também é API →</span>
        </Link>
      </section>
    </div>
  );
}

function Secao({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <section className="border-t border-line py-7 first:border-t-0">
      <p className="kicker mb-3 flex items-center gap-2">
        <AzulejoGlifo size={14} className="text-accent-2/60" />
        {titulo}
      </p>
      <div className="flex max-w-[66ch] flex-col gap-3 font-editorial text-[1.05rem] leading-relaxed text-ink/80">
        {children}
      </div>
    </section>
  );
}

function Compromisso({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <li className="rounded-md border border-line bg-surface p-4">
      <p className="mb-1 font-display text-base font-semibold text-ink">{titulo}</p>
      <p className="font-editorial text-[0.98rem] leading-relaxed text-ink/75">{children}</p>
    </li>
  );
}
