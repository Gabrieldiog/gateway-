class BalcaoError(Exception):
    """Erro de negocio do gateway. O handler em main.py transforma em JSON
    com o status certo, sem vazar stack trace."""

    status_code = 500

    def __init__(self, mensagem: str, detalhes: dict | None = None):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.detalhes = detalhes or {}


class FonteNaoEncontrada(BalcaoError):
    status_code = 404

    def __init__(self, fonte: str, disponiveis: list[str]):
        super().__init__(
            f"fonte desconhecida: {fonte!r}",
            {"fontes_disponiveis": disponiveis},
        )


class RecursoNaoEncontrado(BalcaoError):
    status_code = 404

    def __init__(self, fonte: str, recurso: str, disponiveis: list[str]):
        super().__init__(
            f"recurso desconhecido em {fonte!r}: {recurso!r}",
            {"recursos_disponiveis": disponiveis},
        )


class ParametroInvalido(BalcaoError):
    status_code = 400

    def __init__(self, recurso: str, invalidos: list[str], aceitos: list[str]):
        super().__init__(
            f"parametros invalidos pra {recurso!r}: {', '.join(invalidos)}",
            {"parametros_aceitos": aceitos},
        )


class ChaveFaltando(BalcaoError):
    """A fonte exige chave de API e ela nao esta configurada no ambiente."""

    status_code = 503

    def __init__(self, fonte: str, variavel: str):
        super().__init__(
            f"a fonte {fonte!r} exige chave de API; configure {variavel} no .env",
            {"fonte": fonte, "variavel": variavel},
        )


class ErroUpstream(BalcaoError):
    """A fonte upstream falhou ou respondeu algo inesperado. Alem da mensagem,
    os detalhes dizem ao cliente se a falha e passageira e quando vale tentar
    de novo, e o que o ErroBox da view usa pra contagem regressiva."""

    status_code = 502

    def __init__(
        self,
        fonte: str,
        upstream_status: int | None = None,
        circuito_aberto: bool = False,
        tente_em_s: int | None = None,
    ):
        detalhes: dict = {"fonte": fonte}
        if upstream_status == 404:
            # nao encontrado na fonte e um 404 nosso, nao falha de gateway
            self.status_code = 404
            mensagem = (
                f"nao encontrado na fonte {fonte!r}, o dado pode nao existir "
                "ou o orgao ainda nao publicou esse recorte"
            )
        elif circuito_aberto:
            mensagem = (
                f"a fonte {fonte!r} falhou varias vezes seguidas e esta em pausa "
                "pra nao sobrecarregar o orgao; em instantes tentamos de novo"
            )
            detalhes["circuito"] = "aberto"
            detalhes["passageiro"] = True
            detalhes["tente_em_s"] = tente_em_s or 30
        else:
            mensagem = (
                f"a fonte oficial {fonte!r} esta fora do ar ou respondeu com erro; "
                "e comum em API de governo e costuma se resolver sozinho em minutos"
            )
            detalhes["passageiro"] = True
            detalhes["tente_em_s"] = tente_em_s or 15
        if upstream_status:
            detalhes["status_upstream"] = upstream_status
        super().__init__(mensagem, detalhes)
