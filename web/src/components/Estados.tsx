"use client";

import { useEffect, useState } from "react";
import type { BalcaoError } from "@/lib/api";
import { nomeDaFonte } from "@/lib/fontes";

// o carregando padrão: um spinner em loop, bem visível (inclusive no escuro)
export function Carregando({ texto = "carregando", min }: { texto?: string; min?: number }) {
  return (
    <div
      className="flex flex-col items-center justify-center gap-3 py-10"
      style={min ? { minHeight: min } : undefined}
      role="status"
      aria-live="polite"
      aria-label="carregando"
    >
      <span className="h-9 w-9 animate-spin rounded-full border-[3px] border-line border-t-accent" />
      <span className="num text-xs uppercase tracking-wider text-muted">{texto}…</span>
    </div>
  );
}

// mantém o nome usado nos cadernos; antes era um skeleton de barras (sumia no
// modo escuro), agora reserva a altura equivalente e mostra o spinner.
export function Esqueleto({ linhas = 5 }: { linhas?: number }) {
  return <Carregando min={linhas * 44} />;
}

// traduz a falha pro leitor: quem caiu, se é passageiro e o que vai
// acontecer, com contagem regressiva e nova tentativa sozinha quando a
// falha se declara temporária (fonte fora do ar volta sem ninguém apertar nada)
function explicaErro(erro: BalcaoError): { titulo: string; corpo: string } {
  const fonte = nomeDaFonte(erro.detalhes?.fonte as string | undefined);
  const F = fonte.charAt(0).toUpperCase() + fonte.slice(1);
  if (erro.status === 502 && erro.detalhes?.circuito === "aberto") {
    return {
      titulo: `${F} falhou várias vezes seguidas`,
      corpo:
        "Demos uma pausa nas chamadas pra não sobrecarregar o órgão. Em instantes a gente sonda de novo, se a fonte voltou, tudo reaparece sozinho.",
    };
  }
  if (erro.status === 502) {
    return {
      titulo: `${F} está fora do ar agora`,
      corpo:
        "Isso é comum em API de governo e costuma se resolver sozinho, em minutos. Não é nada do seu lado, a página tenta de novo automaticamente.",
    };
  }
  if (erro.status === 429) {
    return {
      titulo: "Muitas consultas de uma vez",
      corpo: "Passamos do limite por minuto. Um instante e volta ao normal.",
    };
  }
  if (erro.status === 503) {
    return {
      titulo: "Falta uma chave no servidor",
      corpo:
        "Essa fonte exige uma chave de API gratuita que não está configurada aqui. Não depende de você; é ajuste do servidor.",
    };
  }
  if (erro.status === 404) {
    return {
      titulo: "Não encontrado na fonte",
      corpo: `Esse recorte pode não existir, ou ${fonte} ainda não publicou o dado (arquivos diários costumam sair ao longo do dia).`,
    };
  }
  if (erro.status === 400) {
    return { titulo: "Filtro inválido", corpo: erro.message };
  }
  if (erro.status === 0) {
    return {
      titulo: "Sem conexão com o Balcão",
      corpo: "Não conseguimos falar com o servidor. Confira sua internet, a página tenta de novo sozinha.",
    };
  }
  return { titulo: "Algo deu errado", corpo: erro.message };
}

export function ErroBox({ erro, aoTentar }: { erro: BalcaoError; aoTentar?: () => void }) {
  const disponiveis =
    (erro.detalhes?.fontes_disponiveis as string[] | undefined) ??
    (erro.detalhes?.recursos_disponiveis as string[] | undefined) ??
    (erro.detalhes?.parametros_aceitos as string[] | undefined);

  const passageiro =
    erro.detalhes?.passageiro === true ||
    erro.status === 502 ||
    erro.status === 429 ||
    erro.status === 0;
  const sugerido = Number(erro.detalhes?.tente_em_s) || (erro.status === 429 ? 20 : 15);
  const contagemInicial =
    passageiro && aoTentar ? Math.min(Math.max(Math.round(sugerido), 5), 60) : null;

  // contagem regressiva; quando zera, chama o recarregar do caderno.
  // erro novo reinicia a contagem (ajuste no render, sem effect extra)
  const [restam, setRestam] = useState<number | null>(contagemInicial);
  const [erroVisto, setErroVisto] = useState(erro);
  if (erroVisto !== erro) {
    setErroVisto(erro);
    setRestam(contagemInicial);
  }

  useEffect(() => {
    if (restam == null || restam <= 0 || !aoTentar) return;
    const id = setTimeout(() => {
      if (restam <= 1) {
        setRestam(0);
        aoTentar();
      } else {
        setRestam(restam - 1);
      }
    }, 1000);
    return () => clearTimeout(id);
  }, [restam, aoTentar]);

  const { titulo, corpo } = explicaErro(erro);

  return (
    <div className="rounded-lg border border-dashed border-erro/50 bg-erro/5 p-5">
      <p className="num text-xs uppercase tracking-wider text-erro">
        falha {erro.status > 0 ? `· ${erro.status}` : ""}
        {typeof erro.detalhes?.fonte === "string" && ` · ${erro.detalhes.fonte}`}
      </p>
      <p className="mt-1.5 font-editorial text-lg font-semibold leading-snug text-ink">{titulo}</p>
      <p className="mt-1 max-w-[58ch] font-editorial text-[0.98rem] leading-relaxed text-ink/75">
        {corpo}
      </p>
      {disponiveis && (
        <p className="mt-2 text-sm text-muted">
          disponíveis: <span className="num text-ink">{disponiveis.join(", ")}</span>
        </p>
      )}
      <div className="mt-4 flex flex-wrap items-center gap-3">
        {aoTentar && (
          <button
            onClick={() => {
              setRestam(null);
              aoTentar();
            }}
            className="num rounded-md border border-ink/20 px-3 py-1 text-xs uppercase tracking-wider text-ink transition-colors hover:bg-surface-2"
          >
            tentar agora
          </button>
        )}
        {restam != null && restam > 0 && (
          <span className="num flex items-center gap-2 text-xs text-muted">
            <span className="h-3 w-3 animate-spin rounded-full border-[1.5px] border-line border-t-erro" />
            tentando de novo em {restam}s
          </span>
        )}
        {restam != null && restam <= 0 && (
          <span className="num flex items-center gap-2 text-xs text-muted">
            <span className="h-3 w-3 animate-spin rounded-full border-[1.5px] border-line border-t-erro" />
            tentando…
          </span>
        )}
      </div>
    </div>
  );
}

export function Vazio({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-dashed border-line bg-surface/50 p-8 text-center">
      <p className="font-editorial text-lg italic text-muted">{children}</p>
    </div>
  );
}

// quando um filtro muda, o useBalcao segura os dados antigos enquanto rebusca,
// sem isso a tela parece travada. O conteúdo velho esmaece e o mesmo spinner do
// carregando aparece centralizado por cima, deixando claro que tem coisa vindo.
export function EmTransicao({ ativo, children }: { ativo: boolean; children: React.ReactNode }) {
  return (
    <div className="relative">
      <div
        className={`transition-opacity duration-200 ${ativo ? "pointer-events-none opacity-30" : "opacity-100"}`}
        aria-busy={ativo}
      >
        {children}
      </div>
      {ativo && (
        <div className="pointer-events-none absolute inset-x-0 top-12 z-10 flex justify-center">
          <span className="flex items-center gap-2.5 rounded-full border border-line bg-surface/95 px-4 py-2 shadow-sm backdrop-blur-sm">
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-line border-t-accent" />
            <span className="num text-xs uppercase tracking-wider text-muted">carregando…</span>
          </span>
        </div>
      )}
    </div>
  );
}
