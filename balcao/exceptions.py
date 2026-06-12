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


class ErroUpstream(BalcaoError):
    """A fonte upstream falhou ou respondeu algo inesperado."""

    status_code = 502

    def __init__(self, fonte: str, upstream_status: int | None = None):
        if upstream_status == 404:
            # nao encontrado na fonte e um 404 nosso, nao falha de gateway
            self.status_code = 404
            mensagem = f"nao encontrado na fonte {fonte!r}"
        else:
            mensagem = f"a fonte {fonte!r} esta indisponivel ou respondeu com erro"
        detalhes = {"fonte": fonte}
        if upstream_status:
            detalhes["status_upstream"] = upstream_status
        super().__init__(mensagem, detalhes)
