// Catalogo curado de endpoints por tema, o indice clicavel da API. Cada rota
// vem com filtros de exemplo (uf, ano, termo...) pra o link abrir JSON de verdade.
// O indice SEMPRE-atual e o /v1/fontes (esta lista e a versao narrada, agrupada
// por tema, pra explorar). As 38 fontes aqui espelham as 38 registradas no gateway.

export interface Endpoint {
  path: string; // "/v1/camara/deputados?uf=SP&partido=PT"; vira link BASE+path
  desc: string;
  pattern?: boolean; // rota com {placeholder}: mostrada, mas nao clicavel
}

export interface FonteEndpoints {
  nome: string;
  desc: string;
  chave?: boolean; // depende de token gratuito configurado no servidor
  eps: Endpoint[];
}

export interface TemaEndpoints {
  id: string;
  glifo: string;
  nome: string;
  fontes: FonteEndpoints[];
}

export const TEMAS_ENDPOINTS: TemaEndpoints[] = [
  {
    id: "farmacia",
    glifo: "℞",
    nome: "Farmácia",
    fontes: [
      { nome: "rosario", desc: "Drogaria Rosário · Goiânia (VTEX)", eps: [
        { path: "/v1/rosario/produtos?termo=dipirona", desc: "preço por produto, do mais barato" },
      ] },
      { nome: "alexfarma", desc: "Alexfarma · rede goiana (VTEX)", eps: [
        { path: "/v1/alexfarma/produtos?termo=dipirona", desc: "preço local de Goiânia" },
      ] },
      { nome: "nissei", desc: "Farmácias Nissei · Goiânia (RetailON)", eps: [
        { path: "/v1/nissei/produtos?termo=dipirona", desc: "preço da rede com lojas na cidade" },
      ] },
      { nome: "extrafarma", desc: "Extrafarma · nacional, entrega GO", eps: [
        { path: "/v1/extrafarma/produtos?termo=dipirona", desc: "e-commerce do grupo Pague Menos" },
      ] },
      { nome: "notaparana", desc: "Nota Paraná · menor preço por NFC-e (PR)", eps: [
        { path: "/v1/notaparana/produtos?termo=dipirona&lat=-25.42&lon=-49.27", desc: "preço por loja, inclusive controlado" },
      ] },
    ],
  },
  {
    id: "saude",
    glifo: "✚",
    nome: "Saúde & Sociedade",
    fontes: [
      { nome: "sus", desc: "Ministério da Saúde (CNES)", eps: [
        { path: "/v1/sus/estabelecimentos?uf=GO&tipo=5", desc: "hospitais gerais de Goiás" },
        { path: "/v1/sus/estabelecimentos/2077485", desc: "um estabelecimento pelo CNES" },
      ] },
      { nome: "infodengue", desc: "InfoDengue (Fiocruz)", eps: [
        { path: "/v1/infodengue/alertas?municipio=5208707", desc: "dengue/zika/chik em Goiânia" },
      ] },
      { nome: "educacao", desc: "INEP · IDEB e Censo Escolar", eps: [
        { path: "/v1/educacao/ideb?uf=GO", desc: "IDEB por município de GO" },
        { path: "/v1/educacao/censo?uf=GO", desc: "matrículas, docentes, escolas" },
      ] },
      { nome: "seguranca", desc: "Sinesp/MJ · ocorrências criminais", eps: [
        { path: "/v1/seguranca/panorama?uf=GO", desc: "panorama de Goiás" },
        { path: "/v1/seguranca/ranking", desc: "ranking por estado" },
      ] },
    ],
  },
  {
    id: "politica",
    glifo: "⚖",
    nome: "Política",
    fontes: [
      { nome: "camara", desc: "Câmara dos Deputados", eps: [
        { path: "/v1/camara/deputados?uf=SP&partido=PT", desc: "deputados por UF e partido" },
        { path: "/v1/camara/deputados/204528", desc: "ficha de um deputado" },
        { path: "/v1/camara/deputados/204528/perfil", desc: "perfil consolidado" },
        { path: "/v1/camara/deputados/204528/despesas?ano=2024", desc: "cota parlamentar (CEAP)" },
        { path: "/v1/camara/deputados/204528/discursos", desc: "discursos" },
        { path: "/v1/camara/proposicoes", desc: "proposições em tramitação" },
        { path: "/v1/camara/proposicoes/2234666", desc: "uma proposição" },
        { path: "/v1/camara/votacoes", desc: "votações recentes" },
        { path: "/v1/camara/votacoes/2629954-8", desc: "uma votação" },
        { path: "/v1/camara/votacoes/2629954-8/votos", desc: "voto de cada deputado + placar" },
        { path: "/v1/camara/votacoes/2629954-8/orientacoes", desc: "orientação dos partidos" },
      ] },
      { nome: "senado", desc: "Senado Federal", eps: [
        { path: "/v1/senado/senadores?uf=SP", desc: "senadores por UF" },
        { path: "/v1/senado/senadores/6009", desc: "ficha de um senador" },
        { path: "/v1/senado/senadores/6009/votos", desc: "votos de um senador" },
        { path: "/v1/senado/materias", desc: "matérias em tramitação" },
      ] },
    ],
  },
  {
    id: "economia",
    glifo: "$",
    nome: "Economia & Mercado",
    fontes: [
      { nome: "bacen", desc: "Banco Central (SGS) · +190 séries", eps: [
        { path: "/v1/bacen/selic", desc: "taxa Selic" },
        { path: "/v1/bacen/ipca", desc: "IPCA" },
        { path: "/v1/bacen/ipca12m", desc: "IPCA 12 meses" },
        { path: "/v1/bacen/inpc", desc: "INPC" },
        { path: "/v1/bacen/igpm", desc: "IGP-M" },
        { path: "/v1/bacen/igpdi", desc: "IGP-DI" },
        { path: "/v1/bacen/cdi", desc: "CDI" },
        { path: "/v1/bacen/poupanca", desc: "poupança" },
        { path: "/v1/bacen/dolar", desc: "dólar" },
        { path: "/v1/bacen/euro", desc: "euro" },
        { path: "/v1/bacen/serie/433", desc: "qualquer série SGS (433 = IPCA)" },
        { path: "/v1/bacen/inflacao", desc: "painel de inflação" },
        { path: "/v1/bacen/juros-bancos", desc: "juros por banco" },
        { path: "/v1/bacen/reclamacoes", desc: "reclamações por banco" },
      ] },
      { nome: "focus", desc: "Boletim Focus · expectativas do mercado", eps: [
        { path: "/v1/focus/painel", desc: "todas as expectativas" },
        { path: "/v1/focus/ipca", desc: "IPCA" },
        { path: "/v1/focus/selic", desc: "Selic" },
        { path: "/v1/focus/cambio", desc: "câmbio" },
        { path: "/v1/focus/pib", desc: "PIB" },
        { path: "/v1/focus/igpm", desc: "IGP-M" },
        { path: "/v1/focus/inpc", desc: "INPC" },
      ] },
      { nome: "cotacoes", chave: true, desc: "Câmbio & cripto quase em tempo real", eps: [
        { path: "/v1/cotacoes/last/USD-BRL,EUR-BRL,BTC-BRL", desc: "cotação de vários pares" },
      ] },
      { nome: "b3", chave: true, desc: "B3 · ações e índices (via brapi)", eps: [
        { path: "/v1/b3/acoes/PETR4,VALE3,ITUB4", desc: "preço de ações" },
      ] },
      { nome: "tesouro", desc: "Tesouro Nacional (SICONFI)", eps: [
        { path: "/v1/tesouro/uniao", desc: "receita/despesa da União" },
        { path: "/v1/tesouro/uniao/impostos", desc: "impostos da União" },
        { path: "/v1/tesouro/uniao/despesas", desc: "despesa por função" },
        { path: "/v1/tesouro/estados/GO", desc: "um estado" },
        { path: "/v1/tesouro/estados/GO/impostos", desc: "impostos do estado" },
        { path: "/v1/tesouro/estados/GO/despesas", desc: "despesas do estado" },
        { path: "/v1/tesouro/municipios/5208707", desc: "um município (Goiânia)" },
        { path: "/v1/tesouro/municipios/5208707/impostos", desc: "impostos do município" },
        { path: "/v1/tesouro/municipios/5208707/despesas", desc: "despesas do município" },
      ] },
      { nome: "tesourodireto", desc: "Tesouro Direto · preço dos títulos", eps: [
        { path: "/v1/tesourodireto/titulos", desc: "preço e taxa do dia" },
      ] },
      { nome: "ipeadata", desc: "IPEADATA · séries macro e sociais", eps: [
        { path: "/v1/ipeadata/series?q=PIB", desc: "acha o código de uma série" },
        { path: "/v1/ipeadata/serie/BM12_IPCA2012", desc: "valores de uma série" },
      ] },
      { nome: "mundo", desc: "Banco Mundial · Brasil vs mundo", eps: [
        { path: "/v1/mundo/painel", desc: "painel de indicadores do Brasil" },
        { path: "/v1/mundo/comparar?indicador=vida", desc: "comparar (expectativa de vida)" },
        { path: "/v1/mundo/serie?indicador=pib", desc: "uma série ao longo do tempo" },
      ] },
      { nome: "comex", desc: "ComexStat (MDIC) · comércio exterior", eps: [
        { path: "/v1/comex/balanca", desc: "balança comercial" },
        { path: "/v1/comex/ranking", desc: "ranking de exportação/importação" },
      ] },
    ],
  },
  {
    id: "governo",
    glifo: "§",
    nome: "Governo & Transparência",
    fontes: [
      { nome: "transparencia", chave: true, desc: "Portal da Transparência (CGU)", eps: [
        { path: "/v1/transparencia/emendas?ano=2024", desc: "emendas parlamentares" },
        { path: "/v1/transparencia/sancoes?cnpj=00000000000191", desc: "sanções de um CNPJ" },
        { path: "/v1/transparencia/contratos?cnpj=00000000000191", desc: "contratos de um CNPJ" },
        { path: "/v1/transparencia/vinculos?cnpj=00000000000191", desc: "vínculos de uma empresa" },
        { path: "/v1/transparencia/bolsa-familia?municipio=5208707", desc: "Bolsa Família por município" },
      ] },
      { nome: "pncp", desc: "PNCP · licitações e contratos públicos", eps: [
        { path: "/v1/pncp/licitacoes?uf=GO", desc: "licitações" },
        { path: "/v1/pncp/contratos?uf=GO", desc: "contratos" },
        { path: "/v1/pncp/itens", desc: "itens de uma contratação" },
        { path: "/v1/pncp/resultado", desc: "resultado" },
        { path: "/v1/pncp/arquivos", desc: "arquivos" },
      ] },
      { nome: "obrasgov", desc: "Obras federais · situação e valores", eps: [
        { path: "/v1/obrasgov/obras?uf=GO", desc: "obras federais em GO" },
        { path: "/v1/obrasgov/execucao?idProjetoInvestimento=11370.52-41", desc: "execução financeira de uma obra" },
      ] },
      { nome: "datajud", chave: true, desc: "DataJud (CNJ) · processos judiciais", eps: [
        { path: "/v1/datajud/processos/TJGO", desc: "processos de um tribunal" },
        { path: "/v1/datajud/resumo/TJGO", desc: "resumo de um tribunal" },
      ] },
      { nome: "diarios", desc: "Querido Diário · diários oficiais municipais", eps: [
        { path: "/v1/diarios/busca?q=concurso&territorio=5208707", desc: "busca nos diários" },
        { path: "/v1/diarios/cobertura", desc: "cidades cobertas" },
      ] },
      { nome: "tse", desc: "TSE · doações de campanha", eps: [
        { path: "/v1/tse/doacoes?ano=2022&uf=GO", desc: "doações por candidato/partido" },
      ] },
      { nome: "brasilapi", desc: "BrasilAPI · ficha de CNPJ", eps: [
        { path: "/v1/brasilapi/cnpj/00000000000191", desc: "razão social, CNAE, sócios" },
      ] },
    ],
  },
  {
    id: "territorio",
    glifo: "◈",
    nome: "Território, Agro & Clima",
    fontes: [
      { nome: "ibge", desc: "IBGE · estados, municípios, nomes", eps: [
        { path: "/v1/ibge/estados", desc: "estados do Brasil" },
        { path: "/v1/ibge/municipios?uf=GO", desc: "municípios de GO" },
        { path: "/v1/ibge/nomes?nome=maria", desc: "frequência de um nome" },
        { path: "/v1/ibge/nomes/ranking", desc: "nomes mais comuns" },
      ] },
      { nome: "anp", desc: "ANP · preço de combustível", eps: [
        { path: "/v1/anp/precos?combustivel=gasolina&por=estado", desc: "gasolina por estado" },
      ] },
      { nome: "ana", desc: "ANA/SAR · reservatórios", eps: [
        { path: "/v1/ana/reservatorios", desc: "volume dos reservatórios" },
        { path: "/v1/ana/agora", desc: "situação agora" },
        { path: "/v1/ana/principais", desc: "principais reservatórios" },
        { path: "/v1/ana/historico", desc: "histórico" },
      ] },
      { nome: "ons", desc: "ONS · geração do SIN", eps: [
        { path: "/v1/ons/geracao", desc: "geração por fonte, quase em tempo real" },
      ] },
      { nome: "inpe", desc: "INPE · Queimadas e desmatamento", eps: [
        { path: "/v1/inpe/queimadas?por=bioma", desc: "focos de incêndio por bioma" },
        { path: "/v1/inpe/desmatamento", desc: "desmatamento (DETER)" },
      ] },
      { nome: "conab", desc: "CONAB · safra e preços agro", eps: [
        { path: "/v1/conab/safra", desc: "levantamento da safra de grãos" },
        { path: "/v1/conab/precos", desc: "preços agropecuários" },
      ] },
      { nome: "sidra", desc: "IBGE SIDRA · produção e pecuária", eps: [
        { path: "/v1/sidra/producao?produto=soja&ano=2023", desc: "produção de um grão" },
        { path: "/v1/sidra/rebanho?animal=bovino", desc: "rebanho" },
        { path: "/v1/sidra/safra", desc: "safra" },
        { path: "/v1/sidra/abate", desc: "abate" },
        { path: "/v1/sidra/leite", desc: "leite" },
        { path: "/v1/sidra/pib", desc: "PIB municipal" },
        { path: "/v1/sidra/desemprego", desc: "desemprego (PNAD)" },
        { path: "/v1/sidra/rendimento", desc: "rendimento médio" },
      ] },
      { nome: "aneel", desc: "ANEEL (CKAN) · setor elétrico", eps: [
        { path: "/v1/aneel/datasets?q=tarifa", desc: "busca conjuntos de dados" },
        { path: "/v1/aneel/dados/{recurso_id}", desc: "linhas de um recurso, id vem de /datasets", pattern: true },
      ] },
      { nome: "mme", desc: "Minas e Energia (CKAN)", eps: [
        { path: "/v1/mme/datasets?q=energia", desc: "conjuntos de dados" },
        { path: "/v1/mme/dados/{recurso_id}", desc: "linhas de um recurso", pattern: true },
      ] },
      { nome: "antt", desc: "ANTT (CKAN) · transporte terrestre", eps: [
        { path: "/v1/antt/datasets?q=frete", desc: "conjuntos de dados" },
        { path: "/v1/antt/dados/{recurso_id}", desc: "linhas de um recurso", pattern: true },
      ] },
      { nome: "loterias", desc: "Loterias CAIXA · resultados", eps: [
        { path: "/v1/loterias/resultado?loteria=megasena", desc: "último sorteio da Mega-Sena" },
      ] },
    ],
  },
];
