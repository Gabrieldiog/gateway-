# Balcão: Plano de Build

> Um **API gateway** que unifica várias APIs públicas brasileiras atrás de uma única porta: você muda o jeito de chamar e recebe os dados que quer, já normalizados. Tipo um balcão único, você pede do seu jeito, e ele busca em qualquer "repartição" pra você. **Projeto de portfólio** (não é pra operar em produção pra terceiros; é pra demonstrar arquitetura).

Este documento é o briefing pro Claude Code. Cole na raiz do repo como `CLAUDE.md` e trabalhe **um ticket por vez**.

*(Nome "Balcão" é sugestão, troca à vontade. Alternativas: Portão, Tomada, Brasil Único.)*

---

## 1. Posicionamento honesto (leia antes de codar)

Já existem agregadores de dados públicos BR, e o README deve citar isso com orgulho, mostrando que você pesquisou o terreno:

- **BrasilAPI** (10k+ estrelas), CEP, CNPJ, FIPE, bancos, feriados numa API só.
- **mcp-brasil**: 27 APIs públicas expostas pra agentes de IA, com cross-referencing.
- **Base dos Dados**: datalake público no BigQuery; SQL sobre centenas de bases harmonizadas.
- **Portal da Transparência**: API oficial do governo federal.

**Então qual é a graça deste projeto?** Não é "ter as APIs juntas" (isso é roteamento, a parte fácil). O valor, e a história do portfólio, está na **camada que você coloca no meio**, que é o que separa um *gateway* de engenharia de um *proxy* burro:

1. **Normalização** (o coração): cada órgão escreve data, CNPJ e UF de um jeito. O Balcão entrega tudo num schema único e consistente. Você fez o que o governo não fez.
2. **Resiliência**: quando a API da Câmara cai (e cai), o Balcão responde do cache em vez de morrer. Timeout, retry, circuit breaker.
3. **Cache**: não martela a fonte a cada request; respeita os limites de quem está atrás.
4. **Busca unificada**: *uma* chamada que dispara em várias fontes em paralelo e junta o resultado.
5. **Documentação automática** (OpenAPI/Swagger): a API se autodescreve, com cara profissional.
6. **Contrato de conector plugável**: adicionar uma fonte nova = escrever uma classe e registrar. Isso é a decisão de arquitetura que se conta em entrevista.

**Ângulo 2026 (opcional, mas forte):** o que você descreveu ("muda a chamada, vem o dado que você quer") é praticamente um **MCP server**. Expor o mesmo núcleo como MCP (pra Claude/GPT consultarem dados públicos) é a linha de README que faz recrutador técnico parar o scroll hoje. Fica como Fase 4.

**Regra de ouro (a mesma do Florence/Pente Fino): terminar cada fase antes da próxima.** 5 conectores bem-feitos provam o padrão tão bem quanto 27. O avaliador liga pra arquitetura, não pra contagem.

---

## 2. Stack e decisões técnicas

| Camada | Escolha | Por quê |
|---|---|---|
| Linguagem | **Python 3.12** | Onde os SDKs e a comunidade de dados BR vivem. |
| Framework | **FastAPI** | Async-first, type-hinted, gera OpenAPI sozinho. É a escolha mainstream 2025/26 pra API gateway/data platform. |
| Cliente HTTP | **httpx.AsyncClient** | **NUNCA `requests`** em rota async (bloqueia o event loop). Connection pooling, timeouts nativos. |
| Servidor ASGI | **uvicorn** (dev) / gunicorn+uvicorn workers (se for "deployar") | Padrão FastAPI. |
| Validação/Schemas | **Pydantic v2** | Os modelos normalizados (a camada que diferencia o projeto) vivem aqui. |
| Cache | **cachetools** (TTL in-memory) → Redis opcional | Começa simples e sem infra; Redis vira stretch. TTL default 600s. |
| Resiliência | **tenacity** (retry) + circuit breaker próprio | Retry com backoff em falha de upstream; breaker abre quando a fonte está fora e serve cache/erro limpo. |
| Rate limiting | **slowapi** | Função clássica de gateway. Também respeitar limites do upstream. |
| Testes | **pytest** + **httpx.AsyncClient(ASGITransport)** + `dependency_overrides` | Troca conectores por fakes: **testes não tocam a rede** (crucial: o container offline roda a suíte). |
| Observabilidade | logging estruturado + `/health` + `/metrics` | `/metrics` estilo Prometheus é um plus de SRE. |
| Config | **pydantic-settings** (.env) | Chaves de API (Transparência, DataJud) e TTLs fora do código. |
| Empacotamento | **Docker** + docker-compose | "Roda com um comando" impressiona e dispensa manter no ar. |
| MCP (Fase 4) | **FastMCP** | Expõe os conectores como tools de IA reaproveitando o mesmo núcleo. |

### Disciplina async (a pegadinha que derruba projeto)
- Rota que faz I/O (chamar API externa) → `async def` + `await client.get(...)`.
- **Proibido** em rota async: `requests.get()`, `time.sleep()`, leitura de arquivo bloqueante. Use `httpx`, `asyncio.sleep`, `aiofiles`.
- Busca unificada usa `asyncio.gather(...)` pra disparar fontes em paralelo.

---

## 3. Arquitetura (o "junta tudo" mora aqui)

```
                          ┌─────────────────────────────────────────┐
   cliente HTTP  ──►  FastAPI (rotas + OpenAPI)                      │
   (ou agente IA)      │                                             │
                       ▼                                             │
              middleware: rate-limit ▸ cache ▸ logging               │
                       │                                             │
                       ▼                                             │
              ┌──── Connector Registry ────┐   (contrato único)      │
              │  camara   senado   bacen    │                        │
              │  ibge     transparencia ... │                        │
              └──────────────┬──────────────┘                        │
                             ▼                                       │
            httpx.AsyncClient  ──►  APIs públicas (gov.br etc.)      │
                             │                                       │
                             ▼                                       │
                  Normalizer (Pydantic)  ──►  resposta unificada     │
                             ▲                                       │
                    resiliência: retry ▸ circuit breaker ▸ cache ────┘
```

### O contrato de conector (centro de tudo)
Toda fonte implementa a mesma interface; é isso que torna o projeto uma *plataforma*:

```python
# pentefino/connectors/base.py
class BaseConnector(ABC):
    name: str
    base_url: str
    requires_key: bool = False

    @abstractmethod
    async def fetch(self, resource: str, **params) -> NormalizedResponse: ...
    # cada conector traduz params genéricos -> chamada específica da fonte
    # e devolve dados no schema normalizado comum
```

Plugar fonte nova = subclasse + `register()`. Mesma filosofia da engine do Florence e do conector do Pente Fino: **um portfólio com vocabulário de arquitetura consistente**.

### Modos de chamada (responde o "muda o jeito que chama, vem o que quer")
- **Direto por fonte:** `GET /v1/camara/deputados?uf=SP&partido=PT`
- **Recurso normalizado cross-fonte:** `GET /v1/gastos?pessoa=<id>&ano=2025` (decide a fonte internamente)
- **Busca unificada (fan-out):** `GET /v1/buscar?q=<termo>&fontes=camara,senado,transparencia` → dispara em paralelo, junta e devolve.
- **Configuração via query/body:** campos pedidos (`?campos=nome,valor,data`), formato, paginação; o cliente molda a resposta.

---

## 4. As APIs (já mapeadas: Claude Code, use estas)

> Comece com as 🟢 (sem chave). As que precisam de token gratuito ficam pra Fase 3. As 🔴 cruas (arquivo) entram só como demonstração avançada de ETL, se sobrar fôlego.

| Fonte | Base URL | Chave? | O que entrega | Notas |
|---|---|---|---|---|
| **Câmara dos Deputados** 🟢 | `https://dadosabertos.camara.leg.br/api/v2` | Não | deputados, **despesas (CEAP)**, **votações**, proposições | JSON; resposta tem `dados` + `links` (paginação). Docs: `/swagger/api.html`. Endpoints-chave: `/deputados`, `/deputados/{id}/despesas?ano=&mes=`, `/votacoes`, `/proposicoes`. |
| **Senado Federal** 🟢 | `https://legis.senado.leg.br/dadosabertos` | Não | senadores, matérias, **votações**, despesas (CEAPS) | Retorna XML por padrão; pedir JSON via header `Accept: application/json` ou sufixo. |
| **Banco Central (SGS)** 🟢 | `https://api.bcb.gov.br/dados/serie` | Não | Selic, IPCA, câmbio, +190 séries econômicas | Ex.: `/bcdata.sgs.{codigo}/dados?formato=json`. Selic=432, IPCA=433, dólar=1. |
| **IBGE** 🟢 | `https://servicodados.ibge.gov.br/api` | Não | municípios, UFs, população, agregados | `/v1/localidades/municipios`, `/v3/agregados`. Ótimo pra enriquecer joins (id_municipio). |
| **BrasilAPI** 🟢 | `https://brasilapi.com.br/api` | Não | CEP, CNPJ, bancos, FIPE, feriados, DDD | Já é agregadora; útil como conector utilitário (validar CNPJ/CEP). Não abusar (sem full-scan). |
| **Portal da Transparência** 🟡 | `https://api.portaldatransparencia.gov.br` | Token grátis (cadastro) | contratos, despesas, servidores, sanções (CEIS/CNEP), Bolsa Família | Header `chave-api-dados`. Bom pra "sanções de um CNPJ". |
| **PNCP (compras)** 🟡 | `https://pncp.gov.br/api/consulta` | Não (consulta) | contratações, contratos, atas | API de consulta pública; documentação irregular (citar como desafio de qualidade). |
| **DataJud / CNJ** 🟡 | `https://api-publica.datajud.cnj.jus.br` | Chave pública (publicada pelo CNJ) | metadados de processos judiciais | Só capa/movimentações; sigilo e LGPD limitam. Header `Authorization: APIKey ...`. |
| **TSE (eleições)** 🔴 | arquivos em `dadosabertos.tse.jus.br` | Não | candidatos, **doações**, bens, resultados | NÃO é API: CSVs gigantes. Conector "file-backed" (baixa, parseia, serve) = demonstração de ETL. Stretch. |
| **DATASUS** 🔴 | via `pysus` / arquivos DBC | Não/Restrito | internações, nascimentos, mortalidade | DBC arcaico; API moderna (RNDS/e-SUS) restringe por IP (LGPD). Stretch pesado. |

**Conjunto recomendado pro MVP (Fase 1–2):** Câmara, Senado, BACEN, IBGE, BrasilAPI (todas 🟢) + Transparência (🟡, 1 token grátis). Seis fontes provam o conceito com folga.

---

## 5. Estrutura do repositório

```
balcao/
├── README.md                 # pitch + arquitetura + "como chamar" + prints do Swagger
├── CLAUDE.md                 # este documento
├── pyproject.toml
├── docker-compose.yml
├── Dockerfile
├── .env.example              # TRANSPARENCIA_API_KEY=, DATAJUD_API_KEY=, CACHE_TTL=600
├── balcao/
│   ├── main.py               # cria o app FastAPI, monta rotas e middleware
│   ├── config.py             # pydantic-settings
│   ├── http.py               # AsyncClient compartilhado (pool, timeouts) via lifespan
│   ├── cache.py              # TTLCache + chave de cache
│   ├── resilience.py         # retry (tenacity) + circuit breaker
│   ├── ratelimit.py          # slowapi
│   ├── models.py             # schemas normalizados (Pydantic): Despesa, Votacao, Pessoa...
│   ├── connectors/
│   │   ├── base.py           # BaseConnector + NormalizedResponse + registry
│   │   ├── camara.py
│   │   ├── senado.py
│   │   ├── bacen.py
│   │   ├── ibge.py
│   │   ├── brasilapi.py
│   │   └── transparencia.py
│   ├── routers/
│   │   ├── sources.py        # /v1/{fonte}/...  (passthrough normalizado)
│   │   ├── unified.py        # /v1/gastos, /v1/buscar (cross-fonte)
│   │   └── meta.py           # /health, /metrics, /v1/fontes (lista conectores)
│   └── mcp_server.py         # Fase 4 (FastMCP), opcional
├── tests/
│   ├── conftest.py
│   ├── fixtures/             # JSONs gravados das APIs reais (testes offline)
│   ├── test_camara.py
│   ├── test_normalizer.py
│   ├── test_cache.py
│   ├── test_resilience.py
│   └── test_unified.py
└── scripts/
    └── spike.py              # Fase 0
```

---

## 6. Roadmap em fases (cada fase é entregável por si só)

### Fase 0: Spike (de-risk)
Um conector (Câmara) chamando a API real e devolvendo JSON. Provar o fluxo httpx→normalize→responder.
- **Done quando:** `python scripts/spike.py` imprime as despesas de um deputado, normalizadas. ~1 sessão.

### Fase 1: Gateway core (artefato garantido)
App FastAPI com 3+ conectores 🟢 (Câmara, Senado, BACEN, IBGE), middleware de cache + rate-limit + logging, schemas normalizados, `/health`, `/v1/fontes`, e Swagger no ar. Testes offline com fixtures.
- **Done quando:** `docker compose up` sobe a API, o Swagger lista as rotas, e `pytest` passa sem rede.

### Fase 2: Resiliência + busca unificada (a engenharia que diferencia)
Retry + circuit breaker (degrada pra cache quando a fonte cai), normalização robusta (datas, CNPJ, UF padronizados), endpoint `/v1/gastos` cross-fonte e `/v1/buscar` com fan-out paralelo.
- **Done quando:** derrubando uma fonte (fixture de erro), a API responde do cache; `/v1/buscar` junta resultados de 2+ fontes numa chamada. Testado.

### Fase 3: Fontes com chave + qualidade (amplitude)
Plugar Portal da Transparência (token) e PNCP. Documentar no README os problemas de qualidade encontrados (campos faltando, formatos inconsistentes); isso vira protagonista, não rodapé.
- **Done quando:** 6+ fontes ativas; README com a seção "armadilhas de cada API e como o Balcão resolve".

### Fase 4: STRETCH: MCP server
Expor os conectores como tools via FastMCP. README mostra Claude/GPT consultando dados públicos pelo Balcão.
- **Done quando:** um agente faz uma consulta cross-fonte via MCP. Se travar, Fases 1–3 já são um projeto completo.

### Fase 5: STRETCH: conector "hard mode" (TSE)
Conector file-backed: baixa o CSV do TSE, parseia com DuckDB/pandas, serve normalizado. Prova que o mesmo contrato cobre fonte-arquivo, não só API.
- **Done quando:** `/v1/tse/doacoes?ano=2022` responde a partir do arquivo bruto.

---

## 7. Tickets (um por vez, com Definition of Done)

**TICKET-01, Spike Câmara**
`scripts/spike.py` usa httpx.AsyncClient pra GET em `/deputados/{id}/despesas?ano=2025`, mapeia pro schema `Despesa` e imprime.
- *Done:* roda e imprime despesas normalizadas de 1 deputado.

**TICKET-02, Esqueleto FastAPI + contrato de conector**
`main.py` com lifespan criando o AsyncClient compartilhado; `connectors/base.py` (BaseConnector, NormalizedResponse, registry); `/health` e `/v1/fontes` (lista conectores registrados).
- *Done:* `uvicorn` sobe, `/docs` abre, `/v1/fontes` lista o conector da Câmara.

**TICKET-03, Conector Câmara completo + schemas**
Recursos: deputados, despesas, votações, proposições. Modelos Pydantic normalizados em `models.py`. Rotas em `routers/sources.py`.
- *Done:* `/v1/camara/deputados?uf=SP` e `/v1/camara/deputados/{id}/despesas?ano=` respondem normalizado.

**TICKET-04, Cache + rate limit + logging**
TTLCache com chave por (fonte+recurso+params); slowapi (100/min); middleware de logging estruturado (latência, fonte, cache hit/miss).
- *Done:* 2ª chamada idêntica retorna do cache (logado como hit); estourar o limite retorna 429.

**TICKET-05, Mais conectores 🟢 (Senado, BACEN, IBGE)**
Cada um seguindo o contrato. Senado precisa pedir JSON; BACEN é série temporal; IBGE são localidades/agregados.
- *Done:* `/v1/senado/...`, `/v1/bacen/serie/{codigo}`, `/v1/ibge/municipios` respondem normalizado.

**TICKET-06, Testes offline com fixtures**
Gravar respostas reais das APIs em `tests/fixtures/`; testar conectores e normalização com `dependency_overrides` (sem rede). `conftest` com AsyncClient(ASGITransport).
- *Done:* `pytest` verde **sem internet**.

**TICKET-07, Resiliência**
`resilience.py`: retry com backoff (tenacity) e circuit breaker que, com a fonte fora, serve do cache (stale) ou retorna erro limpo e tipado.
- *Done:* teste com fixture de timeout/500 prova fallback pro cache.

**TICKET-08, Busca unificada (fan-out)**
`routers/unified.py`: `/v1/buscar?q=&fontes=` dispara conectores em paralelo (`asyncio.gather`), normaliza e junta; `/v1/gastos` escolhe a fonte certa por tipo de pessoa.
- *Done:* uma chamada retorna resultados mesclados de 2+ fontes; erro em uma fonte não derruba as outras.

**TICKET-09, Docker + README v1**
Dockerfile + docker-compose; README com pitch, diagrama, tabela de fontes, exemplos de chamada (curl), e prints do Swagger.
- *Done:* `docker compose up` sobe tudo; README publicável.

**TICKET-10, Fonte com chave (Transparência)** *(Fase 3)*
Conector com header `chave-api-dados` lido do .env; recursos de contratos/sanções; documentar quirks.
- *Done:* `/v1/transparencia/sancoes?cnpj=` responde; chave fora do código.

*(Fases 4–5 viram tickets quando a 3 fechar.)*

---

## 8. Referências

- **FastAPI Best Practices**: github.com/zhanymkanov/fastapi-best-practices (async, testes com httpx, dependency_overrides).
- **httpx**: async client (substitui `requests` em código async).
- **Câmara API v2**: `dadosabertos.camara.leg.br/swagger/api.html`.
- **Senado Dados Abertos**: `legis.senado.leg.br/dadosabertos`.
- **BACEN SGS**: `api.bcb.gov.br/dados/serie`.
- **IBGE Serviço de Dados**: `servicodados.ibge.gov.br/api`.
- **Portal da Transparência API**: `portaldatransparencia.gov.br/api-de-dados`.
- **PNCP**: `gov.br/pncp` → Dados Abertos.
- **DataJud**: `datajud-wiki.cnj.jus.br/api-publica`.
- **Inspiração (citar como prior art):** BrasilAPI, mcp-brasil, Base dos Dados, Portal da Transparência.

---

## 9. Como usar este doc com o Claude Code

1. Este arquivo vira o `CLAUDE.md` da raiz.
2. Um ticket por vez: "implemente o TICKET-02 seguindo o CLAUDE.md".
3. Não pula fase. Fase 1 fechada já é portfólio; o resto é ganho.
4. Toda quirk de API que aparecer (campo faltando, formato esquisito) → trata na normalização + nota no README. É aí que o projeto deixa de ser proxy e vira engenharia.
5. Regra de ouro: a graça é a **camada do meio** (normalização, resiliência, cache, busca unificada), não a contagem de fontes. 6 conectores sólidos > 27 pela metade.
6. Testes nunca tocam a rede: sempre fixtures + `dependency_overrides`.