"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { apiGet, BalcaoError } from "@/lib/api";

interface Estado<T> {
  dados: T | null;
  carregando: boolean;
  erro: BalcaoError | null;
  ms: number | null;
}

// busca uma URL do proxy do Balcao; refaz quando a url muda e cancela a
// requisicao anterior pra nao pintar resultado fora de ordem. mede a
// latencia da propria chamada pra alimentar o carimbo de cada caderno.
export function useBalcao<T>(url: string | null): Estado<T> & { recarregar: () => void } {
  const [estado, setEstado] = useState<Estado<T>>({
    dados: null,
    carregando: url !== null,
    erro: null,
    ms: null,
  });
  const tick = useRef(0);

  const rodar = useCallback(() => {
    if (url === null) {
      setEstado({ dados: null, carregando: false, erro: null, ms: null });
      return;
    }
    const controle = new AbortController();
    const meu = ++tick.current;
    const t0 = performance.now();
    setEstado((e) => ({ ...e, carregando: true, erro: null }));
    apiGet<T>(url, controle.signal)
      .then((dados) => {
        if (meu === tick.current) {
          setEstado({ dados, carregando: false, erro: null, ms: Math.round(performance.now() - t0) });
        }
      })
      .catch((err) => {
        if (controle.signal.aborted || meu !== tick.current) return;
        const erro = err instanceof BalcaoError ? err : new BalcaoError(String(err), 0);
        setEstado({ dados: null, carregando: false, erro, ms: Math.round(performance.now() - t0) });
      });
    return () => controle.abort();
  }, [url]);

  useEffect(() => rodar(), [rodar]);

  return { ...estado, recarregar: rodar };
}
