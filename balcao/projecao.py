"""Projeção de campos: o cliente pede ?campos=nome,valor,data e o envelope
volta só com esses campos em cada item. É a parte do pitch que deixa o cliente
moldar a resposta — fica aqui, fora dos conectores, pra valer pra toda fonte."""

from balcao.connectors.base import NormalizedResponse
from balcao.exceptions import ParametroInvalido


def parse_campos(valor: str | None) -> list[str]:
    """Quebra o ?campos=a,b,c numa lista limpa, sem vazios nem repetidos
    (preservando a ordem pedida — é o cliente quem manda na ordem das colunas)."""
    if not valor:
        return []
    vistos: list[str] = []
    for parte in valor.split(","):
        campo = parte.strip()
        if campo and campo not in vistos:
            vistos.append(campo)
    return vistos


def aplica_campos(resposta: NormalizedResponse, campos: list[str]) -> NormalizedResponse:
    """Recorta cada item de `dados` pros campos pedidos. Campo inexistente vira
    400 com a lista dos disponíveis — o mesmo contrato de um param errado."""
    if not campos:
        return resposta
    if not resposta.dados:
        # sem itens não dá pra validar os nomes; devolve vazio com a marca
        return resposta.model_copy(update={"meta": {**resposta.meta, "projecao": campos}})

    disponiveis: set[str] = set()
    for item in resposta.dados:
        disponiveis.update(item.keys())
    invalidos = [c for c in campos if c not in disponiveis]
    if invalidos:
        raise ParametroInvalido(resposta.recurso, invalidos, sorted(disponiveis))

    projetados = [{c: item.get(c) for c in campos} for item in resposta.dados]
    return resposta.model_copy(
        update={"dados": projetados, "meta": {**resposta.meta, "projecao": campos}}
    )
