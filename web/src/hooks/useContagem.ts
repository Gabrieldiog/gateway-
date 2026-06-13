"use client";

import { useEffect, useState } from "react";

// conta de 0 até o alvo na montagem, com ease-out. respeita
// prefers-reduced-motion (mostra o valor final direto).
export function useContagem(alvo: number, duracao = 700): number {
  const [valor, setValor] = useState(0);

  useEffect(() => {
    if (!Number.isFinite(alvo)) {
      setValor(0);
      return;
    }
    const reduz =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduz || alvo === 0) {
      setValor(alvo);
      return;
    }
    let raf = 0;
    let inicio: number | null = null;
    const passo = (t: number) => {
      if (inicio === null) inicio = t;
      const p = Math.min((t - inicio) / duracao, 1);
      const eased = 1 - Math.pow(1 - p, 3);
      setValor(alvo * eased);
      if (p < 1) raf = requestAnimationFrame(passo);
      else setValor(alvo);
    };
    raf = requestAnimationFrame(passo);
    return () => cancelAnimationFrame(raf);
  }, [alvo, duracao]);

  return valor;
}
