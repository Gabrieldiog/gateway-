"""Base de Dados VDE (Sinesp / Ministério da Justiça): as ocorrências
criminais do país inteiro, município a município, mês a mês. Não é API,
é um ZIP de 35 MB com um CSV por ano (2015→hoje), cada um com ~1 milhão de
linhas. O conector baixa o ZIP uma vez pro disco e, quando alguém pede um
ano, lê aquele CSV por streaming e monta um índice pequeno agregado por UF
e por tipo de crime.

Quirks tratados aqui: o número real fica em duas colunas conforme o crime,
'total' pros crimes de ocorrência (roubo, furto), 'total_vitima' pros de
vítima (homicídio, estupro), e o outro vem zero; a data é dd/mm/aaaa mensal
(dia sempre 1); e há eventos que são de bombeiro/administração (alvará,
vistoria) que o caderno de segurança não mostra."""

import asyncio
import csv
import io
import os
import tempfile
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from balcao.exceptions import ErroUpstream

URL_VDE = (
    "https://dados.mj.gov.br/dataset/210b9ae2-21fc-4986-89c6-2006eb4db247/"
    "resource/e9d6cc2b-33f1-468d-ab09-9aa8303c2eba/download/basededadosvde.zip"
)

# os tipos de crime que o caderno mostra (o CSV também traz bombeiro e
# administração: alvará, vistoria, incêndio; que ficam de fora)
EVENTOS = {
    "homicidio": "Homicídio doloso",
    "feminicidio": "Feminicídio",
    "tentativa-homicidio": "Tentativa de homicídio",
    "latrocinio": "Roubo seguido de morte (latrocínio)",
    "lesao-morte": "Lesão corporal seguida de morte",
    "morte-agente": "Morte por intervenção de Agente do Estado",
    "estupro": "Estupro",
    "estupro-vulneravel": "Estupro de vulnerável",
    "roubo-veiculo": "Roubo de veículo",
    "furto-veiculo": "Furto de veículo",
    "roubo-carga": "Roubo de carga",
    "roubo-banco": "Roubo a instituição financeira",
    "trafico": "Tráfico de drogas",
    "arma-apreendida": "Arma de Fogo Apreendida",
    "desaparecida": "Pessoa Desaparecida",
}
LABEL_PARA_SLUG = {label: slug for slug, label in EVENTOS.items()}

# população por UF (Censo 2022): pra taxa por 100 mil no ranking, senão
# comparar SP com o Acre em números absolutos seria estatística de mentira
POP_UF = {
    "RO": 1581196, "AC": 830018, "AM": 3941613, "RR": 636707, "PA": 8120131,
    "AP": 733759, "TO": 1511460, "MA": 6776699, "PI": 3271199, "CE": 8794957,
    "RN": 3302406, "PB": 3974687, "PE": 9058931, "AL": 3127511, "SE": 2211868,
    "BA": 14141626, "MG": 20538718, "ES": 3833712, "RJ": 16055174, "SP": 44411238,
    "PR": 11444380, "SC": 7610361, "RS": 10882965, "MS": 2757013, "MT": 3658649,
    "GO": 7056495, "DF": 2817381,
}
NOME_UF = {
    "RO": "Rondônia", "AC": "Acre", "AM": "Amazonas", "RR": "Roraima", "PA": "Pará",
    "AP": "Amapá", "TO": "Tocantins", "MA": "Maranhão", "PI": "Piauí", "CE": "Ceará",
    "RN": "Rio Grande do Norte", "PB": "Paraíba", "PE": "Pernambuco", "AL": "Alagoas",
    "SE": "Sergipe", "BA": "Bahia", "MG": "Minas Gerais", "ES": "Espírito Santo",
    "RJ": "Rio de Janeiro", "SP": "São Paulo", "PR": "Paraná", "SC": "Santa Catarina",
    "RS": "Rio Grande do Sul", "MS": "Mato Grosso do Sul", "MT": "Mato Grosso",
    "GO": "Goiás", "DF": "Distrito Federal",
}


@dataclass
class Agregado:
    total: int = 0
    feminino: int = 0
    masculino: int = 0
    meses: dict[int, int] = field(default_factory=dict)


def _inteiro(valor: str | None) -> int:
    try:
        return int((valor or "").strip() or 0)
    except ValueError:
        return 0


def _monta(dado: bytes, ano: int) -> dict[str, dict[str, Agregado]]:
    """Agrega o CSV do ano por (UF, crime). Roda numa thread (CPU-bound)."""
    por_uf: dict[str, dict[str, Agregado]] = {}
    leitor = csv.DictReader(io.TextIOWrapper(io.BytesIO(dado), encoding="utf-8-sig", newline=""), delimiter=";")
    for linha in leitor:
        label = linha.get("evento")
        slug = LABEL_PARA_SLUG.get(label)
        if slug is None:  # bombeiro/administração ou crime fora da curadoria
            continue
        uf = (linha.get("uf") or "").strip().upper()
        if uf not in POP_UF:
            continue
        # vítima OU ocorrência: um dos dois é sempre zero
        contagem = _inteiro(linha.get("total_vitima")) + _inteiro(linha.get("total"))
        if contagem == 0:
            continue
        ag = por_uf.setdefault(uf, {}).setdefault(slug, Agregado())
        ag.total += contagem
        ag.feminino += _inteiro(linha.get("feminino"))
        ag.masculino += _inteiro(linha.get("masculino"))
        partes = (linha.get("data_referencia") or "").split("/")
        if len(partes) == 3 and partes[1].isdigit():
            mes = int(partes[1])
            ag.meses[mes] = ag.meses.get(mes, 0) + contagem
    return por_uf


class ArquivosSeguranca:
    FRESCOR_ZIP = 24 * 3600.0  # o MJ republica a base todo mês
    MAX_ANOS = 2  # quantos anos manter indexados em memória

    def __init__(self, client: httpx.AsyncClient, relogio=time.monotonic):
        self.client = client
        self._relogio = relogio
        self.pasta = Path(tempfile.gettempdir()) / "balcao-vde"
        self._cache: dict[int, tuple[dict, float]] = {}
        self._locks: dict[int, asyncio.Lock] = {}
        self._lock_zip = asyncio.Lock()

    async def indice(self, ano: int) -> dict[str, dict[str, Agregado]]:
        guardado = self._cache.get(ano)
        if guardado:
            return guardado[0]
        lock = self._locks.setdefault(ano, asyncio.Lock())
        async with lock:
            guardado = self._cache.get(ano)
            if guardado:
                return guardado[0]
            caminho = await self._garante_zip()
            idx = await asyncio.to_thread(self._le_ano, caminho, ano)
            self._cache[ano] = (idx, self._relogio())
            while len(self._cache) > self.MAX_ANOS:
                del self._cache[next(iter(self._cache))]
            return idx

    @staticmethod
    def _le_ano(caminho: Path, ano: int) -> dict[str, dict[str, Agregado]]:
        membro = f"BancoVDE {ano}.csv"
        try:
            with zipfile.ZipFile(caminho) as z:
                if membro not in z.namelist():
                    return {}  # ano ainda não publicado
                with z.open(membro) as arq:
                    return _monta(arq.read(), ano)
        except (zipfile.BadZipFile, KeyError) as exc:
            raise ErroUpstream("seguranca") from exc

    def _zip_fresco(self, caminho: Path) -> bool:
        if not caminho.exists():
            return False
        return (time.time() - caminho.stat().st_mtime) < self.FRESCOR_ZIP

    async def _garante_zip(self) -> Path:
        caminho = self.pasta / "vde.zip"
        if self._zip_fresco(caminho):
            return caminho
        async with self._lock_zip:
            if self._zip_fresco(caminho):
                return caminho
            self.pasta.mkdir(parents=True, exist_ok=True)
            parcial = caminho.with_suffix(".part")
            try:
                async with self.client.stream("GET", URL_VDE, timeout=httpx.Timeout(300.0)) as resp:
                    resp.raise_for_status()
                    with open(parcial, "wb") as arq:
                        async for pedaco in resp.aiter_bytes(1 << 20):
                            arq.write(pedaco)
                os.replace(parcial, caminho)  # só vira definitivo se baixou inteiro
            except httpx.HTTPStatusError as exc:
                parcial.unlink(missing_ok=True)
                raise ErroUpstream("seguranca", exc.response.status_code) from exc
            except httpx.HTTPError as exc:
                parcial.unlink(missing_ok=True)
                raise ErroUpstream("seguranca") from exc
            return caminho
