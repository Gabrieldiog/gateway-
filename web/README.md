# Balcão: Diário de Dados Públicos (view)

Dashboard web do [Balcão](../README.md): um "jornal de dados públicos" que consome o gateway e mostra Câmara, Senado, Banco Central e IBGE numa interface única, com busca unificada que dispara as fontes em paralelo e mostra a latência e o estado do cache de cada uma.

## Stack

Next.js 16 (App Router) · React 19 · Tailwind v4 · Recharts · TypeScript

A view não fala direto com as APIs do governo: um **route handler** em [`src/app/api/balcao/[...path]/route.ts`](src/app/api/balcao/[...path]/route.ts) repassa as chamadas pro gateway servidor-pra-servidor, então não há CORS e a URL da API fica fora do bundle do cliente.

## Rodando

Precisa do gateway no ar (veja o [README da raiz](../README.md)). Por padrão a view procura a API em `http://127.0.0.1:8000`.

```bash
pnpm install
cp .env.example .env.local   # ajuste BALCAO_API_URL se a API estiver noutro lugar
pnpm dev                     # http://localhost:3000
```

Build de produção:

```bash
pnpm build && pnpm start
```

Com Docker, o `docker compose up` na raiz sobe a API e a view juntas.

## Como está organizado

- `src/app/`: um caderno por rota: capa (busca unificada), `camara`, `senado`, `bacen`, `ibge`, `fontes`
- `src/components/`: masthead, índice, carimbo de cache, gráficos, busca unificada
- `src/hooks/`: `useBalcao` (fetch com cancelamento e latência), `useContagem` (count-up)
- `src/lib/`: tipos do gateway, cliente, formatação BRL/data, store do "pulso"
