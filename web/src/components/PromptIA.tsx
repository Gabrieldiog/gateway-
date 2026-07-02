"use client";

import { useRef, useState } from "react";

// o prompt pronto pra colar em qualquer assistente de IA: ensina a API
// inteira e ainda instrui a IA a narrar o que está fazendo pro usuário
// nunca ficar no escuro.

const PROMPT = `Você é meu assistente para usar o Balcão, um gateway público que unifica os dados abertos do Brasil (Câmara, Senado, Banco Central, IBGE, Tesouro, INPE, ANP e mais 18 fontes oficiais) numa API só.

COMO A API FUNCIONA
- Base: http://localhost:8000 (se eu te passar outra URL, use a minha).
- Descoberta: GET /v1/fontes lista todas as fontes com os recursos e filtros aceitos de cada uma. Comece SEMPRE por aí antes de montar qualquer chamada.
- Padrão: GET /v1/{fonte}/{recurso}?{filtros}. Exemplos reais:
  /v1/camara/deputados?uf=SP&partido=PT
  /v1/bacen/selic?ultimos=10
  /v1/anp/precos?combustivel=gasolina&por=estado
  /v1/inpe/queimadas?por=bioma&data=2026-07-01
- Busca em várias fontes de uma vez: GET /v1/buscar?q=termo&fontes=camara,senado
- A resposta vem sempre no mesmo envelope JSON: { fonte, recurso, dados: [...], total, meta }. Os dados já chegam normalizados: datas em ISO, CNPJ só dígitos, UF em sigla.
- meta.cache diz de onde veio: "hit" (memória), "miss" (foi à fonte agora), "stale" (a fonte oficial caiu e o gateway serviu a cópia recente que guardou).

SE DER ERRO
- 400: algum filtro é inválido — a própria resposta lista os aceitos; corrija e tente de novo.
- 404: essa fonte/recurso/dado não existe (ou o arquivo do dia ainda não foi publicado pelo órgão).
- 429: passou de 100 chamadas por minuto — espere um pouco antes de continuar.
- 502: a fonte oficial está fora do ar; isso é comum em API de governo e costuma voltar em minutos — tente de novo.
- 503: essa fonte exige chave de API que não está configurada no servidor.

O QUE EU ESPERO DE VOCÊ (importante!)
1. Antes de cada chamada, me diga em UMA frase o que vai buscar e por quê.
2. Depois de cada resposta, explique o que veio em linguagem simples, sem jargão, citando a fonte oficial e a data do dado.
3. Se der erro, me explique o que aconteceu em termos humanos e o que você vai fazer a respeito.
4. Nunca invente número: se o dado não veio, diga que não veio.
5. No final, resuma o que encontrou e sugira uma próxima pergunta que eu poderia fazer.

Minha primeira pergunta é: [escreva aqui o que você quer saber]`;

export function PromptIA() {
  const [copiado, setCopiado] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  async function copia() {
    try {
      await navigator.clipboard.writeText(PROMPT);
      setCopiado(true);
      if (timer.current) clearTimeout(timer.current);
      timer.current = setTimeout(() => setCopiado(false), 2500);
    } catch {
      // clipboard bloqueado (http sem tls etc) — o leitor ainda pode selecionar o texto
    }
  }

  return (
    <div className="rounded-lg border border-line bg-surface">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-5 py-3">
        <p className="num text-xs uppercase tracking-wider text-muted">
          prompt pronto · cole no seu assistente de IA
        </p>
        <button
          onClick={copia}
          className={`num rounded-md border px-3 py-1.5 text-xs uppercase tracking-wider transition-colors ${
            copiado
              ? "border-emerald-600 bg-emerald-600 text-white"
              : "border-accent bg-accent text-surface hover:opacity-90"
          }`}
        >
          {copiado ? "copiado!" : "copiar prompt"}
        </button>
      </div>
      <pre className="max-h-96 overflow-auto whitespace-pre-wrap px-5 py-4 font-mono text-[0.78rem] leading-relaxed text-ink/85">
        {PROMPT}
      </pre>
    </div>
  );
}
