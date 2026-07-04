"use client";

import { ThemeProvider as NextThemesProvider } from "next-themes";

// next-themes injeta o script que aplica a classe antes do paint (sem flash)
// e persiste a escolha; usamos attribute="class" pra casar com o .dark do CSS.
// A edição começa sempre no modo claro (o papel). O storageKey versionado
// zera uma vez a preferência antiga de quem já testou — sem travar o toggle,
// que segue persistindo a escolha do leitor daqui pra frente.
export function ThemeProvider({ children }: { children: React.ReactNode }) {
  return (
    <NextThemesProvider
      attribute="class"
      defaultTheme="light"
      enableSystem={false}
      storageKey="balcao-edicao-v2"
    >
      {children}
    </NextThemesProvider>
  );
}
