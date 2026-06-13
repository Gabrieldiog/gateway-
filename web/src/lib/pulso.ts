// store minúsculo do "pulso" da última chamada à API: latência medida no
// cliente e o estado de cache que veio no meta. o masthead assina isso pra
// mostrar a saúde do gateway com dado real, sem inventar métrica agregada.

import { useSyncExternalStore } from "react";

export interface Pulso {
  ms: number;
  cache: string | null;
  em: number;
}

let atual: Pulso | null = null;
const ouvintes = new Set<() => void>();

export function registraPulso(p: Pulso) {
  atual = p;
  ouvintes.forEach((fn) => fn());
}

function subscribe(fn: () => void) {
  ouvintes.add(fn);
  return () => ouvintes.delete(fn);
}

export function usePulso(): Pulso | null {
  return useSyncExternalStore(
    subscribe,
    () => atual,
    () => null,
  );
}
