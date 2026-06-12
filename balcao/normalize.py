"""Normalizadores compartilhados: cada fonte escreve data, documento e UF
de um jeito, e aqui tudo converge pro mesmo formato."""

import re
from datetime import date, datetime

UFS = {
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS",
    "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC",
    "SE", "SP", "TO",
}


def so_digitos(valor: str | None) -> str | None:
    if not valor:
        return None
    digitos = re.sub(r"\D", "", str(valor))
    return digitos or None


def para_data(valor: str | None) -> date | None:
    # as fontes mandam "2025-01-15", "2025-01-15T00:00:00" ou nada
    if not valor:
        return None
    try:
        return datetime.fromisoformat(str(valor)).date()
    except ValueError:
        return None


def limpa_texto(valor: str | None) -> str:
    if not valor:
        return ""
    return " ".join(str(valor).split()).rstrip(".")


def normaliza_uf(valor: str | None) -> str | None:
    if not valor:
        return None
    uf = str(valor).strip().upper()
    return uf if uf in UFS else None
