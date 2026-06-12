#!/usr/bin/env python3
"""Grava respostas reais das APIs em tests/fixtures/, truncadas pra
ficarem pequenas. Rodar quando quiser atualizar as fixturas:

    python scripts/grava_fixtures.py
"""

import asyncio
import json
from pathlib import Path

import httpx

DESTINO = Path(__file__).parent.parent / "tests" / "fixtures"

ALVOS = {
    "camara_deputados": (
        "https://dadosabertos.camara.leg.br/api/v2/deputados",
        {"siglaUf": "SP", "itens": 3, "ordem": "ASC", "ordenarPor": "nome"},
    ),
    "camara_deputado_detalhe": (
        "https://dadosabertos.camara.leg.br/api/v2/deputados/204528",
        {},
    ),
    "camara_despesas": (
        "https://dadosabertos.camara.leg.br/api/v2/deputados/204528/despesas",
        {"ano": 2025, "itens": 3},
    ),
    "camara_votacoes": (
        "https://dadosabertos.camara.leg.br/api/v2/votacoes",
        {"itens": 3},
    ),
    "camara_proposicoes": (
        "https://dadosabertos.camara.leg.br/api/v2/proposicoes",
        {"siglaTipo": "PL", "ano": 2025, "itens": 3},
    ),
    "bacen_selic": (
        "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/5",
        {"formato": "json"},
    ),
    "ibge_estados": (
        "https://servicodados.ibge.gov.br/api/v1/localidades/estados",
        {"orderBy": "nome"},
    ),
    "ibge_municipios_sp": (
        "https://servicodados.ibge.gov.br/api/v1/localidades/estados/SP/municipios",
        {"orderBy": "nome"},
    ),
    "senado_lista": (
        "https://legis.senado.leg.br/dadosabertos/senador/lista/atual",
        {},
    ),
}


def trunca(dado):
    # corta as listas pra fixture nao virar um arquivo gigante
    if isinstance(dado, list):
        return [trunca(item) for item in dado[:3]]
    if isinstance(dado, dict):
        return {k: trunca(v) for k, v in dado.items()}
    return dado


async def main() -> None:
    DESTINO.mkdir(parents=True, exist_ok=True)
    headers = {"Accept": "application/json", "User-Agent": "balcao-fixtures/0.1"}
    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        for nome, (url, params) in ALVOS.items():
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            corpo = trunca(resp.json())
            arquivo = DESTINO / f"{nome}.json"
            arquivo.write_text(
                json.dumps(corpo, ensure_ascii=False, indent=1) + "\n",
                encoding="utf-8",
            )
            print(f"{arquivo.name}: ok")


if __name__ == "__main__":
    asyncio.run(main())
