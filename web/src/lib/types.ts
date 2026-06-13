// espelham os schemas normalizados do Balcao (balcao/models.py)

export interface NormalizedResponse<T> {
  fonte: string;
  recurso: string;
  dados: T[];
  total: number | null;
  meta: Record<string, unknown>;
}

export interface Deputado {
  fonte: string;
  id: number;
  nome: string;
  partido: string | null;
  uf: string | null;
  legislatura: number | null;
  email: string | null;
  foto: string | null;
  situacao: string | null;
}

export interface Despesa {
  fonte: string;
  deputado_id: number;
  ano: number;
  mes: number;
  tipo: string;
  fornecedor: string;
  fornecedor_doc: string | null;
  data: string | null;
  valor: string;
  url_documento: string | null;
}

export interface Senador {
  fonte: string;
  id: number;
  nome: string;
  partido: string | null;
  uf: string | null;
  email: string | null;
  foto: string | null;
}

export interface PontoSerie {
  fonte: string;
  serie: number;
  nome: string | null;
  data: string | null;
  valor: string;
}

export interface Estado {
  fonte: string;
  id: number;
  sigla: string;
  nome: string;
  regiao: string | null;
}

export interface Municipio {
  fonte: string;
  id: number;
  nome: string;
  uf: string | null;
  regiao: string | null;
}

export interface ResultadoBusca {
  tipo_resultado: string;
  [campo: string]: unknown;
}

export interface BuscaOut {
  q: string;
  fontes_consultadas: string[];
  total: number;
  resultados: ResultadoBusca[];
  erros: Record<string, string>;
  meta: Record<string, unknown>;
}

export interface GastosOut {
  fonte: string;
  deputado: Deputado;
  ano: number;
  total_documentos: number;
  valor_total: string;
  por_tipo: Record<string, string>;
}

export interface Fonte {
  nome: string;
  base_url: string;
  precisa_chave: boolean;
  descricao: string;
  recursos: Record<string, string>;
}

export interface FontesOut {
  total: number;
  fontes: Fonte[];
}

export interface ErroBalcao {
  erro: string;
  detalhes?: Record<string, unknown>;
}
