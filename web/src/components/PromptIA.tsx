"use client";

import { useRef, useState } from "react";
import { useBalcao } from "@/hooks/useBalcao";
import { caminho } from "@/lib/api";
import type { Fonte, FontesOut } from "@/lib/types";

// o prompt pronto pra colar em qualquer assistente de IA. Ensina a API
// inteira — como chamar cada dado, como acender só as fontes que interessam,
// como ler o erro — e ainda instrui a IA a narrar o que faz. O catálogo das
// fontes é montado AO VIVO do próprio /v1/fontes: nunca envelhece, e lista
// exatamente os recursos e filtros que o servidor aceita neste momento.

const NUCLEO = (catalogo: string, base: string, fontesTxt: string) => `Você é meu assistente para consultar o Balcão, um gateway que unifica os dados abertos do Brasil (${fontesTxt} — Câmara, Senado, Banco Central, IBGE, INPE, ANP, Tesouro e muitas outras) numa API só, já normalizada.

━━ COMO A API FUNCIONA ━━
- Base: ${base} (se eu te passar outra URL, use a minha).
- Toda chamada segue o mesmo formato: GET /v1/{fonte}/{recurso}?{filtros}
- A resposta vem sempre no mesmo envelope JSON: { fonte, recurso, total, dados: [...], meta }.
  Os dados já chegam normalizados: datas em ISO (AAAA-MM-DD), CNPJ só dígitos, UF em sigla.
- meta.cache diz de onde veio o dado: "hit" (veio da memória), "miss" (buscou na fonte agora), "stale" (a fonte oficial caiu e o gateway serviu a cópia recente que tinha guardado).

━━ COMO PEDIR EXATAMENTE O DADO QUE EU QUERO ━━
1. DESCUBRA primeiro: GET /v1/fontes devolve a lista das fontes, os recursos de cada uma e os filtros que cada recurso aceita. É o índice vivo — na dúvida, consulte antes de montar a chamada.
2. UM DADO ESPECÍFICO: monte GET /v1/{fonte}/{recurso} e use os filtros pra estreitar. Exemplos:
   /v1/camara/deputados?uf=SP&partido=PT      → deputados de SP no PT
   /v1/bacen/selic?ultimos=10                 → as 10 últimas taxas Selic
   /v1/anp/precos?combustivel=gasolina&por=estado
   /v1/inpe/queimadas?por=bioma&data=2026-07-01
   Os filtros (entre parênteses no catálogo abaixo) são como você DEIXA DE FORA o que não interessa: peça só a UF, o ano ou o produto que importam.
3. VÁRIAS FONTES DE UMA VEZ — acender umas e apagar outras: GET /v1/buscar?q={termo}&fontes={lista}
   /v1/buscar?q=educacao&fontes=camara,senado  → dispara SÓ essas duas em paralelo e junta o resultado
   /v1/buscar?q=educacao                        → sem "fontes", bate em TODAS as fontes de uma vez
   Uma fonte que falhe não derruba as outras: você recebe o que respondeu.
   Obs.: não existe seleção de campo por "?campos=". Pra reduzir o que volta, use os filtros do recurso (item 2) e, entre fontes, o parâmetro "fontes" (item 3).

━━ O CATÁLOGO COMPLETO (todos os dados que o Balcão serve) ━━
${catalogo}

━━ SE DER ERRO ━━
- 400: algum filtro está inválido — a própria resposta lista os aceitos; corrija e repita.
- 404: essa fonte/recurso não existe, ou o arquivo do dia ainda não foi publicado pelo órgão.
- 429: passou de 2000 chamadas por minuto — espere alguns segundos antes de continuar.
- 502: a fonte oficial está fora do ar (comum em API de governo; costuma voltar em minutos) — tente de novo; se meta.cache vier "stale", é a cópia recente que o gateway guardou.
- 503: essa fonte exige uma chave de API que não está configurada no servidor.

━━ O QUE EU ESPERO DE VOCÊ ━━
1. Antes de cada chamada, me diga em UMA frase o que vai buscar e por quê.
2. Depois de cada resposta, explique o que veio em linguagem simples, sem jargão, citando a fonte oficial e a data do dado.
3. Se der erro, me explique em termos humanos o que aconteceu e o que você vai fazer a respeito.
4. Nunca invente número: se o dado não veio, diga que não veio.
5. No final, resuma o que encontrou e sugira uma próxima pergunta que eu poderia fazer.

Minha primeira pergunta é: [escreva aqui o que você quer saber]`;

const CATALOGO_OFFLINE =
  "(Rode GET /v1/fontes pra ver a lista completa e atualizada — o servidor estava fora de alcance quando este prompt foi gerado.)";

function montaCatalogo(fontes: Fonte[]): string {
  return fontes
    .map((f) => {
      const chave = f.precisa_chave ? " [requer chave de API]" : "";
      const recursos = Object.entries(f.recursos)
        .map(([r, desc]) => `    · /v1/${f.nome}/${r} — ${desc}`)
        .join("\n");
      return `▸ ${f.nome}${chave} — ${f.descricao}\n${recursos}`;
    })
    .join("\n\n");
}

export function PromptIA({ base = "https://balcao-api.onrender.com" }: { base?: string }) {
  const { dados } = useBalcao<FontesOut>(caminho("fontes"));
  const [copiado, setCopiado] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const catalogo = dados?.fontes.length ? montaCatalogo(dados.fontes) : CATALOGO_OFFLINE;
  const totalFontes = dados?.fontes.length ?? null;
  const fontesTxt = totalFontes ? `${totalFontes} fontes oficiais` : "dezenas de fontes oficiais";
  const prompt = NUCLEO(catalogo, base, fontesTxt);

  async function copia() {
    try {
      await navigator.clipboard.writeText(prompt);
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
          {totalFontes != null && (
            <span className="text-accent-2"> · {totalFontes} fontes vivas</span>
          )}
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
        {prompt}
      </pre>
    </div>
  );
}
