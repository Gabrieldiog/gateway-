"use client";

import { useEffect, useRef, useState } from "react";

// igual ao count-up, mas anima do valor ATUAL até o novo alvo; então quando
// a cotação muda de 5,18 pra 5,19 o número desliza entre os dois, sem voltar a
// zero. Na primeira montagem conta de 0 (efeito de entrada). Respeita
// prefers-reduced-motion.
export function useTicker(alvo: number, duracao = 600): number {
  const [valor, setValor] = useState(0);
  const atualRef = useRef(0);

  useEffect(() => {
    if (!Number.isFinite(alvo)) {
      setValor(0);
      atualRef.current = 0;
      return;
    }
    const reduz =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const de = atualRef.current;
    if (reduz || de === alvo) {
      setValor(alvo);
      atualRef.current = alvo;
      return;
    }
    let raf = 0;
    let inicio: number | null = null;
    const passo = (t: number) => {
      if (inicio === null) inicio = t;
      const p = Math.min((t - inicio) / duracao, 1);
      const eased = 1 - Math.pow(1 - p, 3);
      const v = de + (alvo - de) * eased;
      atualRef.current = v;
      setValor(v);
      if (p < 1) raf = requestAnimationFrame(passo);
      else {
        atualRef.current = alvo;
        setValor(alvo);
      }
    };
    raf = requestAnimationFrame(passo);
    return () => cancelAnimationFrame(raf);
  }, [alvo, duracao]);

  return valor;
}
