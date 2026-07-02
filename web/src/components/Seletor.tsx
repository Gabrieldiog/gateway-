"use client";

import type { SelectHTMLAttributes } from "react";

// select nativo vestido com a identidade do jornal: mantém teclado, leitor de
// tela e o picker do celular; a moldura, a setinha e o traço de baixo é que
// são nossos. className vai no invólucro (largura, margens).
export function Seletor({
  className = "",
  ...props
}: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <span className={`relative inline-flex ${className}`}>
      <select
        {...props}
        className="num w-full cursor-pointer appearance-none rounded-md border border-line bg-surface py-1.5 pl-3 pr-8 text-sm text-ink shadow-[inset_0_-2px_0_var(--color-line)] transition-colors hover:border-accent focus:border-accent focus:outline-none focus:shadow-[inset_0_-2px_0_var(--color-accent)] disabled:cursor-not-allowed disabled:opacity-50"
      />
      <svg
        aria-hidden="true"
        viewBox="0 0 12 12"
        className="pointer-events-none absolute right-2.5 top-1/2 h-3 w-3 -translate-y-1/2 text-accent"
      >
        <path
          d="M2.5 4.5 6 8l3.5-3.5"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </span>
  );
}
