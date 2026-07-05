import Link from "next/link";
import type { ReactNode } from "react";
import { CadernoHeader } from "@/components/Caderno";

function Secao({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <section className="border-t border-line py-7 first:border-t-0">
      <p className="kicker mb-3">{titulo}</p>
      <div className="flex max-w-[66ch] flex-col gap-3 font-editorial text-[1.05rem] leading-relaxed text-ink/80">
        {children}
      </div>
    </section>
  );
}

function Rota({ children }: { children: ReactNode }) {
  return (
    <code className="num rounded bg-surface-2 px-1.5 py-0.5 text-[0.85em] text-accent-2">{children}</code>
  );
}

export default function CadernoTermos() {
  return (
    <div>
      <CadernoHeader
        numero="XXXIX"
        kicker="Desenvolvedores"
        titulo="Termos de Uso"
        resumo="A parte séria em uma página: de onde vêm os dados e sob que licença, o que o Balcão promete (e o que não promete), os limites de uso da API e como creditar a fonte. Sem letra miúda escondida."
      />

      <Secao titulo="A licença dos dados">
        <p>
          Tudo que o Balcão entrega é <strong>dado público</strong>, aberto por
          lei: a Lei de Acesso à Informação (12.527/2011) e a Política de Dados
          Abertos do Executivo federal (Decreto 8.777/2016) obrigam os órgãos a
          publicar essas bases pra qualquer pessoa usar, inclusive
          comercialmente. O Balcão não é dono de nada disso — ele só reorganiza,
          normaliza e serve o que já é seu por direito.
        </p>
        <p>
          Cada número tem um dono original, e ele é sempre creditado: o{" "}
          <Link href="/fontes" className="text-accent hover:underline">
            Expediente
          </Link>{" "}
          lista as fontes oficiais, e todo caderno mostra de onde puxou o dado,
          com link pra origem.
        </p>
      </Secao>

      <Secao titulo="O que o Balcão promete — e o que não promete">
        <p>
          <strong>Promete honestidade:</strong> nenhum número aqui é inventado,
          arredondado por conveniência ou preenchido no chute. Quando a fonte
          não informa, o Balcão diz &ldquo;não informado&rdquo; em vez de
          fingir um zero. Quando uma fonte cai, ele avisa qual caiu.
        </p>
        <p>
          <strong>Não promete disponibilidade:</strong> este é um{" "}
          <strong>projeto de portfólio</strong>, não um serviço contratado. Pode
          sair do ar, mudar de rota ou ficar para trás quando um órgão muda sua
          API. Não use o Balcão como peça crítica de outro sistema em produção —
          vá direto na fonte oficial pra isso. Os dados são fornecidos
          &ldquo;como estão&rdquo;, sem garantia.
        </p>
      </Secao>

      <Secao titulo="Os limites de uso">
        <p>
          A API aceita <strong>2000 requisições por minuto</strong> por balde.
          Anônimo, seu balde é o seu IP — o que significa que você divide a cota
          com todo mundo atrás do mesmo IP (escritório, faculdade, operadora).
          Com uma <strong>chave de acesso</strong>, você ganha um balde só seu:
          mande-a no cabeçalho <Rota>X-API-Key</Rota> ou na query{" "}
          <Rota>?chave=</Rota>. Toda resposta traz os cabeçalhos{" "}
          <Rota>X-RateLimit-Limit</Rota>, <Rota>X-RateLimit-Remaining</Rota> e{" "}
          <Rota>X-RateLimit-Reset</Rota> pra você saber onde está.
        </p>
        <p>
          Em troca, um pedido: <strong>não martele as fontes</strong>. O Balcão
          já cacheia e respeita os limites dos órgãos por você — respeite os dele
          também. Uso abusivo derruba o serviço pra todo mundo.
        </p>
      </Secao>

      <Secao titulo="A referência da API">
        <p>
          A API se autodescreve. A referência interativa (com &ldquo;testar no
          navegador&rdquo; e exemplos de código em várias linguagens) fica em{" "}
          <Rota>/scalar</Rota>; o Swagger clássico em <Rota>/docs</Rota>; e o
          contrato bruto em <Rota>/openapi.json</Rota>. O{" "}
          <Link href="/docs" className="text-accent hover:underline">
            Manual da API
          </Link>{" "}
          explica em português como chamar cada fonte, com exemplos.
        </p>
      </Secao>

      <Secao titulo="Ao reusar, credite">
        <p>
          Se você construir algo em cima do Balcão, cite a fonte original do
          dado (o órgão público), não o Balcão — ele é só o balcão de
          atendimento, não a repartição. E, se der, mencione que passou por
          aqui: é o que mantém um projeto aberto vivo.
        </p>
      </Secao>
    </div>
  );
}
