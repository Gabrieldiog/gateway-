"use client";

import {
  Children,
  isValidElement,
  useEffect,
  useId,
  useRef,
  useState,
  type ChangeEvent,
  type KeyboardEvent,
  type OptionHTMLAttributes,
  type ReactNode,
} from "react";

// dropdown com a identidade do jornal em aberto E fechado — o <select> nativo
// só deixa vestir a caixa fechada; a lista aberta é do sistema operacional.
// Aqui é uma listbox própria (botão + lista), com teclado e leitor de tela.
// Mantém a API do <select>: value, onChange({target:{value}}) e <option> filhos,
// pra as páginas não mudarem nada.

interface SeletorProps {
  value?: string | number;
  onChange?: (e: ChangeEvent<HTMLSelectElement>) => void;
  children: ReactNode;
  className?: string;
  disabled?: boolean;
  "aria-label"?: string;
}

interface Opcao {
  value: string;
  label: string;
}

function extraiOpcoes(children: ReactNode): Opcao[] {
  const fora: Opcao[] = [];
  Children.forEach(children, (filho) => {
    if (!isValidElement(filho)) return;
    const props = filho.props as OptionHTMLAttributes<HTMLOptionElement>;
    const label = typeof props.children === "string" ? props.children : String(props.children ?? "");
    const value = props.value != null ? String(props.value) : label;
    fora.push({ value, label });
  });
  return fora;
}

export function Seletor({
  value,
  onChange,
  children,
  className = "",
  disabled = false,
  "aria-label": ariaLabel,
}: SeletorProps) {
  const opcoes = extraiOpcoes(children);
  const atual = String(value ?? "");
  const selecionada = opcoes.find((o) => o.value === atual) ?? opcoes[0];

  const [aberto, setAberto] = useState(false);
  const [foco, setFoco] = useState(0);
  const raiz = useRef<HTMLDivElement>(null);
  const listaId = useId();

  // fecha ao clicar fora
  useEffect(() => {
    if (!aberto) return;
    function fora(e: MouseEvent) {
      if (raiz.current && !raiz.current.contains(e.target as Node)) setAberto(false);
    }
    document.addEventListener("mousedown", fora);
    return () => document.removeEventListener("mousedown", fora);
  }, [aberto]);

  function escolhe(opcao: Opcao) {
    setAberto(false);
    if (opcao.value !== atual) {
      onChange?.({ target: { value: opcao.value } } as unknown as ChangeEvent<HTMLSelectElement>);
    }
  }

  function abre() {
    if (disabled) return;
    const i = opcoes.findIndex((o) => o.value === atual);
    setFoco(i < 0 ? 0 : i);
    setAberto(true);
  }

  function tecla(e: KeyboardEvent) {
    if (disabled) return;
    if (!aberto) {
      if (e.key === "ArrowDown" || e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        abre();
      }
      return;
    }
    if (e.key === "Escape") {
      setAberto(false);
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      setFoco((f) => Math.min(opcoes.length - 1, f + 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setFoco((f) => Math.max(0, f - 1));
    } else if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      if (opcoes[foco]) escolhe(opcoes[foco]);
    }
  }

  return (
    <div ref={raiz} className={`relative inline-flex ${className}`}>
      <button
        type="button"
        disabled={disabled}
        aria-haspopup="listbox"
        aria-expanded={aberto}
        aria-label={ariaLabel}
        onClick={() => (aberto ? setAberto(false) : abre())}
        onKeyDown={tecla}
        className="num flex min-h-11 w-full cursor-pointer items-center justify-between gap-2 rounded-md border border-line bg-surface py-1.5 pl-3 pr-2.5 text-sm text-ink shadow-[inset_0_-2px_0_var(--color-line)] transition-colors hover:border-accent focus:border-accent focus:shadow-[inset_0_-2px_0_var(--color-accent)] focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
      >
        <span className="truncate">{selecionada?.label ?? ""}</span>
        <svg
          aria-hidden="true"
          viewBox="0 0 12 12"
          className={`h-3 w-3 shrink-0 text-accent transition-transform duration-200 ${aberto ? "rotate-180" : ""}`}
        >
          <path d="M2.5 4.5 6 8l3.5-3.5" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>

      {aberto && (
        <ul
          role="listbox"
          id={listaId}
          aria-label={ariaLabel}
          className="absolute left-0 top-[calc(100%+4px)] z-40 max-h-72 min-w-full overflow-auto rounded-md border border-line bg-surface py-1 shadow-[4px_4px_0_rgba(28,26,23,0.1)] dark:shadow-[4px_4px_0_rgba(0,0,0,0.4)]"
        >
          {opcoes.map((o, i) => {
            const escolhida = o.value === atual;
            return (
              <li
                key={o.value + i}
                role="option"
                aria-selected={escolhida}
                onMouseEnter={() => setFoco(i)}
                onClick={() => escolhe(o)}
                className={`num flex min-h-11 cursor-pointer items-center gap-2 whitespace-nowrap px-3 text-sm transition-colors ${
                  i === foco ? "bg-accent/10" : ""
                } ${escolhida ? "font-semibold text-accent" : "text-ink"}`}
              >
                <span className="w-3 shrink-0 text-accent">{escolhida ? "✓" : ""}</span>
                {o.label}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
