"""Conector file-backed: o histórico COMPLETO de votos de um deputado num ano.

A API da Câmara é por votação, então o voto-a-voto de um ano inteiro sairia em
centenas de chamadas. Os arquivos anuais de dados abertos trazem tudo de uma vez:
- votacoesVotos-{ano}.json (~70MB): todo voto nominal do ano (votação, deputado, voto)
- votacoes-{ano}.json (~11MB): a descrição e o resultado de cada votação

Baixa os dois e monta um índice em memória por streaming (ijson, pico ~100MB,
não os 300MB de um json.load), servindo qualquer deputado instantâneo depois. O
índice fica em cache por ano (poucos MB cada), limitado aos anos mais recentes."""

import asyncio
import io
import time
from dataclasses import dataclass
from datetime import date

import httpx
import ijson

from balcao.exceptions import ErroUpstream
from balcao.normalize import limpa_texto


@dataclass
class IndiceAno:
    ano: int
    por_deputado: dict[int, list[dict]]  # deputado_id -> [{votacao_id, voto, data}]
    por_votacao: dict[str, dict]  # votacao_id -> {descricao, data, aprovada, orgao}


def _monta(votos_bytes: bytes, votacoes_bytes: bytes, ano: int) -> IndiceAno:
    """Parse pesado (CPU-bound), roda numa thread pra não travar o event loop."""
    por_deputado: dict[int, list[dict]] = {}
    for rec in ijson.items(io.BytesIO(votos_bytes), "dados.item"):
        dep = rec.get("deputado_") or {}
        did = dep.get("id")
        if did is None:
            continue
        por_deputado.setdefault(int(did), []).append(
            {
                "votacao_id": rec.get("idVotacao"),
                "voto": limpa_texto(rec.get("voto")),
                "data": (rec.get("dataHoraVoto") or "")[:10] or None,
            }
        )

    por_votacao: dict[str, dict] = {}
    for v in ijson.items(io.BytesIO(votacoes_bytes), "dados.item"):
        ap = v.get("aprovacao")
        por_votacao[v.get("id")] = {
            "descricao": limpa_texto(v.get("descricao")),
            "data": v.get("data"),
            "aprovada": bool(ap) if ap is not None else None,
            "orgao": v.get("siglaOrgao"),
        }
    return IndiceAno(ano=ano, por_deputado=por_deputado, por_votacao=por_votacao)


class ArquivoVotos:
    BASE = "https://dadosabertos.camara.leg.br/arquivos"
    MAX_ANOS = 2  # quantos anos manter indexados em memória
    # o arquivo do ano corrente cresce a cada sessão do plenário: o índice
    # dele vence e é remontado sozinho. Ano fechado é história, não vence.
    FRESCOR_ANO_CORRENTE = 6 * 3600.0

    def __init__(self, client: httpx.AsyncClient, relogio=time.monotonic):
        self.client = client
        self._relogio = relogio
        self._cache: dict[int, tuple[IndiceAno, float]] = {}
        self._locks: dict[int, asyncio.Lock] = {}

    def _vencido(self, ano: int, montado_em: float) -> bool:
        if ano < date.today().year:
            return False
        return self._relogio() - montado_em > self.FRESCOR_ANO_CORRENTE

    async def indice(self, ano: int) -> IndiceAno:
        guardado = self._cache.get(ano)
        if guardado and not self._vencido(ano, guardado[1]):
            return guardado[0]
        # o lock evita dois requests baixarem o mesmo arquivo de 70MB ao mesmo tempo
        lock = self._locks.setdefault(ano, asyncio.Lock())
        async with lock:
            guardado = self._cache.get(ano)
            if guardado and not self._vencido(ano, guardado[1]):
                return guardado[0]
            idx = await self._baixa_e_monta(ano)
            self._cache[ano] = (idx, self._relogio())
            while len(self._cache) > self.MAX_ANOS:  # descarta o ano mais antigo
                del self._cache[next(iter(self._cache))]
            return idx

    async def _baixa_e_monta(self, ano: int) -> IndiceAno:
        votos_url = f"{self.BASE}/votacoesVotos/json/votacoesVotos-{ano}.json"
        votacoes_url = f"{self.BASE}/votacoes/json/votacoes-{ano}.json"
        # falha no download ou arquivo corrompido vira erro upstream limpo (502),
        # não um 500 cru estourando do ijson
        try:
            rv, rc = await asyncio.gather(
                self.client.get(votos_url, timeout=httpx.Timeout(120.0)),
                self.client.get(votacoes_url, timeout=httpx.Timeout(60.0)),
            )
            rv.raise_for_status()
            rc.raise_for_status()
            return await asyncio.to_thread(_monta, rv.content, rc.content, ano)
        except httpx.HTTPStatusError as exc:
            raise ErroUpstream("camara", exc.response.status_code) from exc
        except (httpx.HTTPError, ijson.JSONError) as exc:
            raise ErroUpstream("camara") from exc
