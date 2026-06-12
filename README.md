# Balcão 🇧🇷

> **API gateway que unifica APIs públicas brasileiras atrás de uma única porta.**
> Você pede do seu jeito — o Balcão busca na "repartição" certa e devolve os dados **normalizados**, com cache, resiliência e busca unificada.

⚠️ **Projeto de portfólio em construção** — demonstração de arquitetura, não um serviço de produção.

## A ideia

Já existem ótimos agregadores de dados públicos BR ([BrasilAPI](https://brasilapi.com.br), [Base dos Dados](https://basedosdados.org), [Portal da Transparência](https://portaldatransparencia.gov.br)). O valor deste projeto não é "ter as APIs juntas" — é a **camada do meio**, que separa um gateway de engenharia de um proxy burro:

1. **Normalização** — cada órgão escreve data, CNPJ e UF de um jeito; o Balcão entrega um schema único.
2. **Resiliência** — timeout, retry e circuit breaker; quando a fonte cai, responde do cache.
3. **Cache** — respeita os limites de quem está atrás.
4. **Busca unificada** — uma chamada dispara várias fontes em paralelo e junta o resultado.
5. **OpenAPI/Swagger** — a API se autodescreve.
6. **Conectores plugáveis** — fonte nova = uma classe + `register()`.

## Stack

Python 3.12+ · FastAPI · httpx (async) · Pydantic v2 · cachetools · tenacity · slowapi · pytest · Docker

## Fontes planejadas

Câmara dos Deputados · Senado Federal · Banco Central (SGS) · IBGE · BrasilAPI · Portal da Transparência

## Status

- [x] Fase 0 — Spike (conector Câmara provando o fluxo httpx → normalização → resposta)
- [ ] Fase 1 — Gateway core (FastAPI + conectores + cache + rate-limit + Swagger)
- [ ] Fase 2 — Resiliência + busca unificada
- [ ] Fase 3 — Fontes com chave (Transparência, PNCP)
- [ ] Fase 4 — MCP server (stretch)

> O plano completo de build está em [CLAUDE.md](CLAUDE.md).
