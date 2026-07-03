"use client";

import { useState } from "react";

// texto longo nunca morre num "...": corta no limite e oferece o resto.
// Texto curto passa reto, sem botão.
export function LerMais({
  texto,
  limite = 180,
  className = "",
}: {
  texto: string;
  limite?: number;
  className?: string;
}) {
  const [aberto, setAberto] = useState(false);
  if (!texto || texto.length <= limite) {
    return <p className={className}>{texto}</p>;
  }
  return (
    <p className={className}>
      {aberto ? texto : `${texto.slice(0, limite).trimEnd()}… `}
      <button
        type="button"
        onClick={() => setAberto((a) => !a)}
        className="num ml-1 text-[0.68rem] uppercase tracking-wider text-accent transition-colors hover:text-accent-2"
      >
        {aberto ? "ler menos" : "ler mais"}
      </button>
    </p>
  );
}
