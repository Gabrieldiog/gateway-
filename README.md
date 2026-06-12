# Balcão

> **Um API gateway que unifica APIs públicas brasileiras atrás de uma única porta.**
> Você pede do seu jeito — o Balcão descobre a "repartição" certa, traduz a chamada, e devolve os dados **normalizados**, com cache, retry, circuit breaker e busca unificada.

Projeto de portfólio: o objetivo é demonstrar arquitetura de gateway, não operar como serviço para terceiros.

## Por que isso existe

Já existem ótimos agregadores de dados públicos BR — [BrasilAPI](https://brasilapi.com.br), [mcp-brasil](https://github.com/mcp-brasil), [Base dos Dados](https://basedosdados.org) e o próprio [Portal da Transparência](https://portaldatransparencia.gov.br). Juntar APIs é a parte fácil. O valor deste projeto está na **camada do meio**, que separa um gateway de engenharia de um proxy burro:

1. **Normalização** — cada órgão escreve data, CNPJ e UF de um jeito; aqui tudo sai num schema único.
2. **Resiliência** — retry com backoff pra falha passageira, circuit breaker pra fonte caída, e fallback pra cache stale: a API responde mesmo com a fonte fora do ar.
3. **Cache em dois níveis** — o fresco poupa a fonte; o velho segura a barra quando ela cai.
4. **Busca unificada** — uma chamada dispara várias fontes em paralelo e junta o resultado.
5. **Erros que ajudam** — filtro errado responde 400 com a lista dos aceitos; recurso errado, 404 com os disponíveis.
6. **Conectores plugáveis** — fonte nova = uma subclasse + `@register`.

## Arquitetura

```
cliente HTTP ──► FastAPI (rotas + OpenAPI)
                    │
                    ▼
        middleware: rate limit ▸ cache ▸ logging JSON
                    │
                    ▼
          ┌── Connector Registry ──┐     contrato único:
          │ camara  senado  bacen  │     fetch(recurso, **params)
          │ ibge    ...            │     -> NormalizedResponse
          └───────────┬────────────┘
                      ▼
        httpx.AsyncClient (pool compartilhado)
        retry ▸ circuit breaker ▸ fallback stale
                      │
                      ▼
            APIs públicas (gov.br etc.)
```

## Como chamar

**Direto por fonte** — filtros com nomes nossos, o conector traduz pros da fonte:

```bash
curl "localhost:8000/v1/camara/deputados?uf=SP&partido=PL"
curl "localhost:8000/v1/camara/deputados/204528/despesas?ano=2025"
curl "localhost:8000/v1/bacen/selic?ultimos=10"        # atalhos: selic, cdi, ipca, igpm, dolar, euro
curl "localhost:8000/v1/bacen/serie/433?data_inicio=2026-01-01&data_fim=2026-03-31"
curl "localhost:8000/v1/ibge/municipios?uf=SP"
curl "localhost:8000/v1/senado/senadores?uf=SP&partido=PSD"
```

**Busca unificada** — fan-out paralelo, erro numa fonte não derruba as outras:

```bash
curl "localhost:8000/v1/buscar?q=silva&fontes=camara,senado"
curl "localhost:8000/v1/buscar?q=campinas"               # sem fontes= busca em todas
```

**Recurso cross-fonte** — resolve o parlamentar por id ou nome e agrega:

```bash
curl "localhost:8000/v1/gastos?deputado=Adriana&uf=SP&ano=2025"
```

**Descoberta** — a API se autodescreve:

```bash
curl "localhost:8000/v1/fontes"      # conectores, recursos e filtros de cada um
open http://localhost:8000/docs      # Swagger
```

Toda resposta de fonte vem no mesmo envelope:

```json
{
  "fonte": "camara",
  "recurso": "deputados",
  "dados": [{"id": 204528, "nome": "Adriana Ventura", "partido": "NOVO", "uf": "SP"}],
  "total": 1,
  "meta": {"pagina": 1, "tem_proxima": true, "cache": "hit"}
}
```

## Rodando

Com Docker:

```bash
docker compose up --build
```

Sem Docker:

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/uvicorn balcao.main:app --reload
```

Testes (a suite roda **sem internet** — as fixtures gravadas respondem no lugar das APIs):

```bash
.venv/bin/python -m pytest
```

## Fontes ativas

| Fonte | Recursos | Chave? |
|---|---|---|
| Câmara dos Deputados | deputados, despesas (CEAP), votações, proposições | não |
| Senado Federal | senadores em exercício, detalhe | não |
| Banco Central (SGS) | Selic, CDI, IPCA, IGP-M, câmbio e qualquer série por código | não |
| IBGE | estados, municípios | não |
| Portal da Transparência | contratos, sanções *(planejado)* | token grátis |

## As armadilhas de cada fonte (e como o Balcão resolve)

A parte divertida de unificar dados públicos é descobrir que **cada API tem suas manias**. Algumas encontradas até aqui:

- **BACEN manda data em `dd/mm/aaaa`** (e exige o mesmo formato na consulta). O Balcão fala ISO 8601 com o mundo e traduz nos dois sentidos.
- **A série completa do SGS volta décadas de pontos** se você não recortar. Sem filtro, o conector assume `ultimos=20` em vez de baixar tudo.
- **No IBGE, a UF de um município mora 3 níveis abaixo** (`municipio.microrregiao.mesorregiao.UF`) — e o caminho muda conforme a divisão territorial da resposta. Sai plano: `{"uf": "SP", "regiao": "Sudeste"}`.
- **O Senado responde XML por padrão** (JSON só com header `Accept`) e enterra a lista em `ListaParlamentarEmExercicio.Parlamentares.Parlamentar`. E a lista atual **não aceita filtro**: o recorte por UF/partido é feito no gateway.
- **A Câmara devolve CNPJ ora com máscara, ora sem**, datas ora com hora, ora sem, ora nulas, e textos com espaços duplicados e ponto final solto. Os normalizadores aplainam tudo.
- **O endpoint de despesas da Câmara já degradou em produção** durante o desenvolvimento — respondendo 200 com lista vazia pra qualquer deputado. É exatamente o cenário do fallback stale: se a fonte cai e existe resposta recente em cache, o Balcão serve o dado velho com aviso em `meta` em vez de quebrar.
- **Registro podre não derruba o lote**: item que falha validação é descartado e contado em `meta.descartados`.

## Stack

Python 3.12+ · FastAPI · httpx (async, pool único) · Pydantic v2 · cachetools · tenacity · slowapi · pytest (offline, `MockTransport`) · Docker

## Roadmap

- [x] Fase 0 — Spike (fluxo httpx → normalização → resposta)
- [x] Fase 1 — Gateway core: conectores, cache, rate limit, logging, Swagger, testes offline
- [x] Fase 2 — Resiliência (retry + breaker + stale) e busca unificada
- [ ] Fase 3 — Fontes com chave (Portal da Transparência, PNCP)
- [ ] Fase 4 — Dashboard web e MCP server (consultas por agentes de IA)
