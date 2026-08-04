# Balcão

> **Um API gateway que unifica APIs públicas brasileiras atrás de uma única porta.**
> Você pede do seu jeito, o Balcão descobre a "repartição" certa, traduz a chamada, e devolve os dados **normalizados**, com cache, retry, circuit breaker e busca unificada.

Projeto de portfólio: o objetivo é demonstrar arquitetura de gateway, não operar como serviço para terceiros.

**Ao vivo:** [balcaoo.netlify.app](https://balcaoo.netlify.app), o Diário de Dados Públicos (a view web) · [balcao-api.onrender.com/docs](https://balcao-api.onrender.com/docs), a API, com Swagger pra testar cada rota no navegador.

> A API roda no plano grátis do Render, que dorme quando ninguém usa; a primeira chamada do dia pode levar alguns segundos pra acordar.

## Por que isso existe

Já existem ótimos agregadores de dados públicos BR: [BrasilAPI](https://brasilapi.com.br), [mcp-brasil](https://github.com/mcp-brasil), [Base dos Dados](https://basedosdados.org) e o próprio [Portal da Transparência](https://portaldatransparencia.gov.br). Juntar APIs é a parte fácil. O valor deste projeto está na **camada do meio**, que separa um gateway de engenharia de um proxy burro:

1. **Normalização**: cada órgão escreve data, CNPJ e UF de um jeito; aqui tudo sai num schema único.
2. **Resiliência**: retry com backoff pra falha passageira, circuit breaker pra fonte caída, e fallback pra cache stale: a API responde mesmo com a fonte fora do ar.
3. **Cache em dois níveis**: o fresco poupa a fonte; o velho segura a barra quando ela cai.
4. **Busca unificada**: uma chamada dispara várias fontes em paralelo e junta o resultado.
5. **Erros que ajudam**: filtro errado responde 400 com a lista dos aceitos; recurso errado, 404 com os disponíveis.
6. **Conectores plugáveis**: fonte nova = uma subclasse + `@register`.

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

Os exemplos abaixo já apontam pra **API no ar**; é só colar no terminal (a primeira pode demorar uns segundos, cold start do Render).

**Direto por fonte**: filtros com nomes nossos, o conector traduz pros da fonte:

```bash
curl "https://balcao-api.onrender.com/v1/camara/deputados?uf=SP&partido=PL"
curl "https://balcao-api.onrender.com/v1/camara/deputados/204528/despesas?ano=2025"
curl "https://balcao-api.onrender.com/v1/camara/votacoes/2629954-8/votos"   # voto de cada deputado + placar no meta
curl "https://balcao-api.onrender.com/v1/bacen/selic?ultimos=10"        # atalhos: selic, cdi, ipca, igpm, dolar, euro
curl "https://balcao-api.onrender.com/v1/bacen/serie/433?data_inicio=2026-01-01&data_fim=2026-03-31"
curl "https://balcao-api.onrender.com/v1/ibge/municipios?uf=SP"
curl "https://balcao-api.onrender.com/v1/senado/senadores?uf=SP&partido=PSD"
curl "https://balcao-api.onrender.com/v1/sus/estabelecimentos?uf=SP&tipo=5"  # hospitais gerais; tipo é o código CNES
curl "https://balcao-api.onrender.com/v1/sidra/producao?produto=soja&ano=2023"  # produção de soja por estado
curl "https://balcao-api.onrender.com/v1/sidra/rebanho?animal=bovino&municipio=5107925"  # rebanho num município
curl "https://balcao-api.onrender.com/v1/ipeadata/series?q=PIB"          # acha o código da série
curl "https://balcao-api.onrender.com/v1/ipeadata/serie/BM12_IPCA2012?ultimos=12"  # valores recentes
curl "https://balcao-api.onrender.com/v1/aneel/datasets?q=tarifa"        # busca conjuntos num portal CKAN
curl "https://balcao-api.onrender.com/v1/aneel/dados/{recurso_id}"       # linhas reais de um recurso (datastore)
```

**Busca unificada**: fan-out paralelo, erro numa fonte não derruba as outras:

```bash
curl "https://balcao-api.onrender.com/v1/buscar?q=silva&fontes=camara,senado"
curl "https://balcao-api.onrender.com/v1/buscar?q=campinas"               # sem fontes= busca em todas
```

**Recurso cross-fonte**: resolve o parlamentar por id ou nome e agrega:

```bash
curl "https://balcao-api.onrender.com/v1/gastos?deputado=Adriana&uf=SP&ano=2025"
```

**Descoberta**: a API se autodescreve:

```bash
curl "https://balcao-api.onrender.com/v1/fontes"      # conectores, recursos e filtros de cada um
open https://balcao-api.onrender.com/docs             # Swagger
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

## Dashboard

Tem uma view web em [`web/`](web/), um "diário de dados públicos" com **mais de vinte cadernos** sobre o gateway: do telão de energia ao vivo do ONS ao semáforo de dengue da sua cidade, passando por arrecadação, emendas, sanções, Bolsa Família, câmbio/ouro/cripto/bolsa em tempo real, queimadas, preço da gasolina e Tesouro Direto, com **busca unificada** que dispara as fontes em paralelo e mostra a latência e o estado do cache de cada uma ao vivo. Next.js 16 + Tailwind + Recharts, falando com a API por um proxy server-to-server (sem CORS). Detalhes no [README da view](web/README.md).

## MCP: consultas por agentes de IA

O mesmo núcleo é exposto como um servidor [MCP](https://modelcontextprotocol.io) (via FastMCP), pra um agente (Claude, etc.) consultar dados públicos com ferramentas. O passe livre é **`consultar(fonte, recurso, params)`**, qualquer recurso das 25 fontes, e os atalhos cobrem as perguntas mais comuns: `buscar`, `deputados`, `gastos`, `senadores`, `serie_economica`, `municipios`, `arrecadacao`, `energia_agora`, `preco_combustivel` e `listar_fontes`. A lógica é a mesma que responde no HTTP: a busca em leque e os conectores vivem em [`balcao/search.py`](balcao/search.py) e são reusados pelas duas portas.

```bash
pip install -e ".[mcp]"
python -m balcao.mcp_server      # stdio, pra plugar num cliente MCP
```

## Rodando

Com Docker (sobe a API e a dashboard juntas):

```bash
docker compose up --build
# API em http://localhost:8000 · dashboard em http://localhost:3000
```

Sem Docker:

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/uvicorn balcao.main:app --reload
```

Testes (a suite roda **sem internet**, as fixtures gravadas respondem no lugar das APIs):

```bash
.venv/bin/python -m pytest
```

## Fontes ativas (25)

| Fonte | Recursos | Chave? |
|---|---|---|
| Câmara dos Deputados | deputados, despesas (CEAP), votações, voto por deputado (inclusive o histórico anual por arquivo), proposições | não |
| Senado Federal | senadores, histórico de votos por senador, matérias em tramitação (API nova) | não |
| Banco Central (SGS) | Selic, CDI, IPCA, IGP-M, poupança, câmbio e qualquer série por código + painel de custo de vida | não |
| Boletim Focus (Olinda) | o que o mercado espera pra IPCA, Selic, câmbio, PIB e IGP-M por ano | não |
| IBGE | estados, municípios | não |
| Ministério da Saúde (CNES) | estabelecimentos de saúde: hospitais, UBS, prontos-socorros | não |
| Tesouro Nacional (SICONFI) | arrecadação (impostos + contribuições), imposto a imposto e despesa por função, para União, estados e municípios, com ranking | não |
| Tesouro Direto | preço e taxa do dia de cada título público (CSV de 14 MB garimpado) | não |
| IBGE SIDRA (agro) | produção agrícola (PAM) e pecuária por estado/município | não |
| ANEEL · MME · ANTT (CKAN) | datasets e linhas reais (datastore) de energia, mineração e transporte | não |
| IPEADATA | séries macro, regionais e sociais | não |
| AwesomeAPI (câmbio) | dólar, euro, libra, ouro e cripto quase em tempo real, com plano B em fontes abertas (Frankfurter/BCE, gold-api e Binance) quando ela recusa | não |
| B3 via brapi | ações e Ibovespa (~15 min de atraso; fan-out de 1 ativo por chamada) | token grátis |
| ONS | geração do SIN por fonte quase em tempo real + % renovável | não |
| INPE Queimadas | focos de incêndio do dia por estado, bioma e município (CSV diário) | não |
| InfoDengue (Fiocruz) | dengue, zika e chikungunya por município com nível de alerta semanal | não |
| Portal da Transparência (CGU) | emendas parlamentares, sanções (CEIS+CNEP) por CNPJ/CPF, Bolsa Família por município | token grátis |
| PNCP | licitações e contratos públicos de todas as esferas (Lei 14.133) | não |
| ComexStat (MDIC) | balança comercial mês a mês e rankings por país, UF e produto | não |
| ANP | preço de gasolina, etanol, diesel, GNV e GLP por estado/município (coletas reais nos postos) | não |
| DataJud (CNJ) | capa e movimentações de processos por tribunal + o que mais se processa | chave pública |
| TSE | doações de campanha por candidato, partido, doador e origem (ZIP de até 1,4 GB) | não |

## As armadilhas de cada fonte (e como o Balcão resolve)

A parte divertida de unificar dados públicos é descobrir que **cada API tem suas manias**. Algumas encontradas até aqui:

- **BACEN manda data em `dd/mm/aaaa`** (e exige o mesmo formato na consulta). O Balcão fala ISO 8601 com o mundo e traduz nos dois sentidos.
- **A série completa do SGS volta décadas de pontos** se você não recortar. Sem filtro, o conector assume `ultimos=20` em vez de baixar tudo.
- **No IBGE, a UF de um município mora 3 níveis abaixo** (`municipio.microrregiao.mesorregiao.UF`), e o caminho muda conforme a divisão territorial da resposta. Sai plano: `{"uf": "SP", "regiao": "Sudeste"}`.
- **O Senado responde XML por padrão** (JSON só com header `Accept`) e enterra a lista em `ListaParlamentarEmExercicio.Parlamentares.Parlamentar`. E a lista atual **não aceita filtro**: o recorte por UF/partido é feito no gateway.
- **A Câmara devolve CNPJ ora com máscara, ora sem**, datas ora com hora, ora sem, ora nulas, e textos com espaços duplicados e ponto final solto. Os normalizadores aplainam tudo.
- **O endpoint de despesas da Câmara já degradou em produção** durante o desenvolvimento, respondendo 200 com lista vazia pra qualquer deputado. É exatamente o cenário do fallback stale: se a fonte cai e existe resposta recente em cache, o Balcão serve o dado velho com aviso em `meta` em vez de quebrar.
- **Voto por deputado só existe em votação nominal**: as votações simbólicas (aprovadas "de viva voz") respondem `dados: []`. Em vez de devolver vazio sem explicação, o Balcão põe um `aviso` no `meta`; nas nominais, monta também o `placar` (Sim/Não/Abstenção/Obstrução).
- **O CNES (SUS) não devolve total nem link de próxima página** e identifica o tipo de unidade só por um código numérico. O Balcão pagina com `limite`/`pagina`, traduz `uf` (sigla → código IBGE) e converte o código do tipo no nome legível (`5` → `HOSPITAL GERAL`).
- **Registro podre não derruba o lote**: item que falha validação é descartado e contado em `meta.descartados`.
- **O SICONFI (Tesouro) é lento e cheio de código**: pede o nome exato do anexo (DCA-Anexo I-C pra receita, I-E pra despesa), a coluna certa (`Receitas Brutas Realizadas`, `Despesas Empenhadas`) e o `cod_conta` vem com prefixo de rótulo (`RO1.1.1.0.00.0.0`). O conector resolve tudo isso e devolve só os números que importam: receita, impostos e despesa por função.
- **O SIDRA (IBGE) fala em código**: a resposta é uma lista onde o 1º item é o cabeçalho, as chaves são crípticas (`D1N` = localidade, `D2N` = variável, `D4N` = produto, `V` = valor), e ausência de dado vem como `"-"`, `".."` ou `"X"`. O conector lê o cabeçalho, traduz nomes amigáveis (`produto=soja`, `variavel=quantidade`) pros códigos de tabela/classificação do SIDRA, e devolve registros limpos com o valor já numérico (ou `null`).
- **Muitos portais do governo rodam CKAN** (ANEEL, MME, ANTT...) com a mesma API. Em vez de um conector por órgão, há um **motor CKAN** (`connectors/ckan.py`): plugar um novo portal é uma subclasse com `name` + `base_url`. `/datasets` busca os conjuntos (com a marca de quais têm `datastore`) e `/dados/{id}` traz as linhas reais via `datastore_search`, porque CKAN é catálogo, e nem todo recurso expõe dado tabular (alguns são só CSV pra download).
- **O OData do IPEADATA é mancha**: não aceita `contains` (só `startswith` pra buscar série por nome) e o `ValoresSerie` **ignora `$top`/`$orderby`**, devolve a série inteira, das décadas, em ordem crescente. O conector busca por prefixo, recorta os mais recentes (`ultimos`) do lado de cá e entrega as datas em ISO.
- **O SGS do BACEN responde `{"erro":{}}` com HTTP 200** em certas séries (a 195, índice diário da poupança, quebra no `ultimos/1`). Corpo que não é lista vira resultado vazio, não exceção, e a poupança usa a série mensal (196), que é limpa.
- **O Olinda (Boletim Focus) recusa o `$` percent-encoded**: mandar `%24top` dá 400. A query OData é montada à mão com o cifrão literal, e ainda tem que deduplicar por `baseCalculo` e conviver com nomes de recurso irregulares (`ExpectativasMercadoAnuais` no plural, `ExpectativaMercadoMensais` no singular).
- **O ONS publica o minuto seguinte zerado** antes de ter o dado; o conector volta do fim do dia até achar geração de verdade. E Itaipu vem em campos próprios, contada como hidráulica.
- **O host de dados do INPE migrou** (`queimadas.dgi.inpe.br` morreu; o atual é `dataserver-coids.inpe.br`) e o arquivo do dia enche ao longo das horas: de madrugada, "hoje" quase não tem focos, e isso é honesto, não bug.
- **A Transparência (CGU) manda dinheiro em formato brasileiro** (`"8.000,00"`), datas `dd/mm/aaaa`, e o rate limit muda por horário (mais generoso de madrugada). Valores viram `Decimal`, datas viram ISO, e as sanções consultam CEIS e CNEP em paralelo.
- **O PNCP quer datas `AAAAMMDD` sem separador**, exige a modalidade por um código de enum que só existe num manual em PDF, e o `tamanhoPagina` tem **mínimo de 10** (pedir 2 dá 400). O código virou slug legível (`pregao-eletronico`, `dispensa`). E a fonte cai por horas; o 502 limpo e o cache seguram.
- **A brapi (B3) no plano gratuito só aceita 1 ativo por chamada**: a lista vira fan-out paralelo. E como o dado free tem ~15 min de atraso, a fonte é *cacheável* de propósito (proteger a cota de 15 mil requests/mês), ao contrário do câmbio.
- **O ComexStat manda toda métrica como string** (`"6619343689"`), fala `export`/`import` em inglês, e embrulha tudo em `data.list`. O conector fala português (`exportacao`), devolve `Decimal` e calcula o saldo da balança juntando os dois fluxos em paralelo.
- **O CSV do Tesouro Direto não tem ordem cronológica**: 14 MB desde 2002, com o topo em 2015 e o fim em 2005. A data mais recente é achada comparando `AAAAMMDD` como texto, sem converter 250 mil linhas.
- **O firewall do gov.br (ANP) barra clientes que não pareçam navegador**: 403 pra User-Agent técnico e, descoberto na prática, **401 pro header `Accept: application/json`** que o client compartilhado usa pro Senado. O conector se apresenta como navegador e sobrescreve o Accept. De quebra: BOM UTF-8, campo com `;` embutido entre aspas (split ingênuo quebra) e vírgula decimal.
- **O DataJud é Elasticsearch cru**: um índice por tribunal, query em DSL, resposta enterrada em `hits.hits[]._source`, atrás de uma **chave pública que o CNJ rotaciona** (por isso vive no `.env`). E o CNJ rate-limita agregações pesadas (429). A lista de movimentos não é ordenada: o último andamento é achado pelo `dataHora`.
- **As APIs do Senado morrem com hora marcada**: a de matérias foi desativada em fev/2026 e até a rota "substituta" clássica já passou da própria data de desligamento (mas segue no ar, por inércia). O conector usa a API nova de processos, a primeira do Senado que fala JSON de verdade.
- **O TSE não tem API**: doações de campanha são um **ZIP de 390 MB (2022) a 1,4 GB (2024)** com 112 CSVs latin-1 dentro. O conector baixa por streaming direto pro disco uma única vez (rename atômico pra nunca cachear download pela metade), lê só o CSV da UF pedida de dentro do zip e agrega. CPF de doador pode vir mascarado (LGPD).
- **Portais podem responder 200 com HTML** (página de manutenção, firewall); o `resp.json()` estourava como 500 cru; hoje corpo não-JSON vira **502 tipado** e conta pro circuit breaker.
- **Toda resposta diz de onde veio**: os conectores carregam um **selo de procedência** (`meta.fonte` com nome, URL e nota honesta sobre limitações); a resposta pro "o Google fala outro número".

## Stack

Python 3.12+ · FastAPI · httpx (async, pool único) · Pydantic v2 · cachetools · tenacity · slowapi · ijson (ETL streaming) · pytest (offline, `MockTransport`) · Docker

## O que já tem

- **Gateway core**: conectores plugáveis, cache em dois níveis, rate limit, logging JSON, Swagger e testes offline.
- **Resiliência**: retry com backoff, circuit breaker e fallback pra cache stale quando a fonte cai.
- **Busca unificada**: fan-out paralelo por várias fontes numa chamada só.
- **25 fontes ativas**: parlamento, economia, saúde, dinheiro público, tempo real e conectores de arquivo (ANP, Tesouro Direto e o ZIP de até 1,4 GB do TSE).
- **Dashboard web**: o [Diário de Dados Públicos](https://balcaoo.netlify.app), com mais de vinte cadernos sobre o gateway.
- **Servidor MCP** (FastMCP), os conectores como ferramentas de IA, com passe livre `consultar` sobre as 25 fontes.
- **No ar**: API no Render, dashboard no Netlify (blueprint em `render.yaml`).

Próximo: caderno de compras públicas na view (aguardando o PNCP estabilizar).
