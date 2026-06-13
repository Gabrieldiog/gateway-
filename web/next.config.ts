import type { NextConfig } from "next";
import { fileURLToPath } from "node:url";

const nextConfig: NextConfig = {
  // fixa a raiz no diretório da app: existem outros lockfiles acima na árvore
  // (home do usuário) e o Turbopack inferia a raiz errada.
  turbopack: {
    root: fileURLToPath(new URL(".", import.meta.url)),
  },
};

export default nextConfig;
