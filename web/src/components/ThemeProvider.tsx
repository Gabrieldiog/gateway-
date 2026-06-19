"use client";

import { ThemeProvider as NextThemesProvider } from "next-themes";

// next-themes injeta o script que aplica a classe antes do paint (sem flash)
// e persiste a escolha; usamos attribute="class" pra casar com o .dark do CSS.
export function ThemeProvider({ children }: { children: React.ReactNode }) {
  return (
    <NextThemesProvider attribute="class" defaultTheme="light" enableSystem={false}>
      {children}
    </NextThemesProvider>
  );
}
