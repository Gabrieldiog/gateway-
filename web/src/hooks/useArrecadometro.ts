"use client";

import { useEffect, useState } from "react";

// projeta um valor anual oficial num contador que sobe a cada instante,
// a mesma lógica do Impostômetro de SP: pega o total do ano e distribui pelos
// segundos, mostrando o acumulado estimado até agora. Não é medição por
// segundo (esse dado não existe); é o valor real do ano projetado no tempo.
export function useArrecadometro(anualBase: number): number {
  const [valor, setValor] = useState(0);

  useEffect(() => {
    if (!Number.isFinite(anualBase) || anualBase <= 0) {
      setValor(0);
      return;
    }
    const ano = new Date().getFullYear();
    const inicio = new Date(ano, 0, 1).getTime();
    const duracao = new Date(ano + 1, 0, 1).getTime() - inicio;
    const tick = () => {
      const fracao = Math.min((Date.now() - inicio) / duracao, 1);
      setValor(anualBase * fracao);
    };
    tick();
    const id = setInterval(tick, 100);
    return () => clearInterval(id);
  }, [anualBase]);

  return valor;
}
