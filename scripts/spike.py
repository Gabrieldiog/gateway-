#!/usr/bin/env python3
"""Spike da Fase 0: busca despesas de um deputado na API da Camara e
imprime tudo ja convertido pro schema normalizado Despesa.

Uso:
    python scripts/spike.py
    python scripts/spike.py --uf RJ --ano 2024
    python scripts/spike.py --id 204554
"""

import argparse
import asyncio
import re
import sys
from datetime import date, datetime
from decimal import Decimal

import httpx
from pydantic import BaseModel, ValidationError

BASE_URL = "https://dadosabertos.camara.leg.br/api/v2"
TIMEOUT = httpx.Timeout(15.0, connect=5.0)
HEADERS = {
    "Accept": "application/json",
    "User-Agent": "balcao-spike/0.1 (projeto de portfolio)",
}


class Despesa(BaseModel):
    fonte: str = "camara"
    deputado_id: int
    ano: int
    mes: int
    tipo: str
    fornecedor: str
    fornecedor_doc: str | None  # cnpj ou cpf, so digitos
    data: date | None
    valor: Decimal  # valorLiquido, que e o valor de fato reembolsado
    url_documento: str | None


def so_digitos(valor: str | None) -> str | None:
    if not valor:
        return None
    digitos = re.sub(r"\D", "", valor)
    return digitos or None


def para_data(valor: str | None) -> date | None:
    # a Camara manda "2025-01-15" ou "2025-01-15T00:00:00", as vezes vazio
    if not valor:
        return None
    try:
        return datetime.fromisoformat(valor).date()
    except ValueError:
        return None


def limpa_texto(valor: str | None) -> str:
    if not valor:
        return ""
    return " ".join(valor.split()).rstrip(".")


def normaliza_despesa(bruto: dict, deputado_id: int) -> Despesa:
    return Despesa(
        deputado_id=deputado_id,
        ano=bruto["ano"],
        mes=bruto["mes"],
        tipo=limpa_texto(bruto.get("tipoDespesa")),
        fornecedor=limpa_texto(bruto.get("nomeFornecedor")),
        fornecedor_doc=so_digitos(bruto.get("cnpjCpfFornecedor")),
        data=para_data(bruto.get("dataDocumento")),
        valor=Decimal(str(bruto.get("valorLiquido", "0"))),
        url_documento=bruto.get("urlDocumento") or None,
    )


async def busca_deputados(client: httpx.AsyncClient, uf: str) -> list[dict]:
    resp = await client.get(
        "/deputados",
        params={"siglaUf": uf, "ordem": "ASC", "ordenarPor": "nome", "itens": 10},
    )
    resp.raise_for_status()
    return resp.json()["dados"]


async def busca_despesas(
    client: httpx.AsyncClient, deputado_id: int, ano: int, itens: int = 15
) -> list[dict]:
    resp = await client.get(
        f"/deputados/{deputado_id}/despesas",
        params={"ano": ano, "itens": itens},
    )
    resp.raise_for_status()
    return resp.json()["dados"]


async def roda_spike(uf: str, ano: int, deputado_id: int | None) -> int:
    async with httpx.AsyncClient(
        base_url=BASE_URL, timeout=TIMEOUT, headers=HEADERS
    ) as client:
        if deputado_id is not None:
            candidatos = [{"id": deputado_id, "nome": f"deputado {deputado_id}"}]
        else:
            candidatos = await busca_deputados(client, uf)

        # nem todo deputado tem despesa no ano, entao tenta o proximo da lista
        brutos: list[dict] = []
        escolhido: dict | None = None
        for dep in candidatos:
            brutos = await busca_despesas(client, dep["id"], ano)
            if brutos:
                escolhido = dep
                break

        if escolhido is None:
            print(f"Nenhuma despesa em {ano} pros deputados consultados ({uf}).")
            return 1

        despesas: list[Despesa] = []
        descartadas = 0
        for bruto in brutos:
            try:
                despesas.append(normaliza_despesa(bruto, escolhido["id"]))
            except (ValidationError, KeyError):
                # registro invalido nao derruba o lote inteiro
                descartadas += 1

        print(f"\nDespesas de {escolhido['nome']} (id {escolhido['id']}) - ano {ano}")
        print("-" * 88)
        for d in despesas:
            quando = d.data.isoformat() if d.data else f"{d.ano}-{d.mes:02d}"
            doc = d.fornecedor_doc or "-"
            print(
                f"{quando}  {d.tipo[:34]:<34}  "
                f"{d.fornecedor[:22]:<22}  {doc:>14}  R$ {d.valor:>10.2f}"
            )
        print("-" * 88)
        total = sum(d.valor for d in despesas)
        print(f"{len(despesas)} documentos normalizados", end="")
        if descartadas:
            print(f" ({descartadas} descartados por dado invalido)", end="")
        print(f" - total R$ {total:.2f}\n")
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uf", default="SP", help="UF pra escolher um deputado (default: SP)")
    parser.add_argument("--ano", type=int, default=2025, help="ano das despesas (default: 2025)")
    parser.add_argument("--id", type=int, default=None, help="id de um deputado especifico")
    args = parser.parse_args()
    try:
        return asyncio.run(roda_spike(args.uf.upper(), args.ano, args.id))
    except httpx.HTTPStatusError as exc:
        print(f"Erro da API da Camara: {exc.response.status_code} em {exc.request.url}", file=sys.stderr)
        return 1
    except httpx.HTTPError as exc:
        print(f"Falha de rede ao falar com a Camara: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
