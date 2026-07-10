"""Relay 1v1 do joguinho "Maior ou Menor?".

Isto NÃO é gateway: não chama nenhuma fonte pública nem entra no registro de
conectores. O servidor só faz duas coisas — junta dois jogadores (matchmaking
de fila de um) e repassa, sem ler, tudo que um manda pro outro. As rodadas cada
cliente gera localmente a partir da semente da sala (o mesmo motor do desafio
diário), então aqui não mora regra de jogo nem placar. É de propósito: mantém o
Balcão leve e o modo online é casual, client-side. Como o servidor nunca olha o
conteúdo, um cliente malicioso só engana o próprio oponente — não há dado
sensível trafegando.

Protocolo (mensagens de controle que o servidor emite):
  {"tipo": "procurando"}                          esperando alguém aparecer
  {"tipo": "achou", "sala": ..., "oponente": ...} pareou; a sala vira a semente
  {"tipo": "oponente_saiu"}                        o outro lado caiu

Qualquer outra mensagem é de jogo: chega de um lado e sai igualzinha no outro.
"""

import asyncio
import json
from dataclasses import dataclass
from uuid import uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["multijogador"])

MAX_NOME = 20


@dataclass
class Jogador:
    ws: WebSocket
    nome: str
    sala: str = ""
    oponente: "Jogador | None" = None


# Fila de espera de UM jogador (é 1v1): quem chega e não acha ninguém fica aqui
# até o próximo aparecer. O lock protege a fila porque vários handlers async
# podem mexer nela ao mesmo tempo.
_fila: Jogador | None = None
_lock = asyncio.Lock()


async def _texto(jogador: Jogador, texto: str) -> bool:
    """Manda uma string crua. Devolve False se o socket já era (sem estourar)."""
    try:
        await jogador.ws.send_text(texto)
        return True
    except Exception:
        return False


async def _enviar(jogador: Jogador, payload: dict) -> bool:
    return await _texto(jogador, json.dumps(payload, ensure_ascii=False))


async def _emparelhar(eu: Jogador) -> Jogador | None:
    """Pareia com quem estiver na fila ou entra na fila.

    Devolve o oponente quando pareia; None quando ficou esperando. O laço cobre
    o caso raro do jogador da fila ter caído sem o handler dele ter limpado
    ainda: se o "achou" não chega nele, desfaz e tenta de novo.
    """
    global _fila
    while True:
        async with _lock:
            peer = _fila
            if peer is None:
                _fila = eu
                return None
            _fila = None
            eu.sala = peer.sala = uuid4().hex[:12]
            eu.oponente = peer
            peer.oponente = eu

        if await _enviar(peer, {"tipo": "achou", "sala": eu.sala, "oponente": eu.nome}):
            return peer
        # peer fantasma: desfaz o pareamento e volta pro laço
        peer.oponente = None
        eu.oponente = None


async def _sair(eu: Jogador) -> None:
    """Tira o jogador da fila (se estava) e avisa o oponente que ele saiu."""
    global _fila
    async with _lock:
        if _fila is eu:
            _fila = None
    op = eu.oponente
    if op is not None:
        eu.oponente = None
        op.oponente = None
        await _enviar(op, {"tipo": "oponente_saiu"})


@router.websocket("/ws/1v1")
async def um_contra_um(ws: WebSocket) -> None:
    await ws.accept()
    nome = (ws.query_params.get("nome") or "").strip()[:MAX_NOME] or "Anônimo"
    eu = Jogador(ws=ws, nome=nome)

    peer = await _emparelhar(eu)
    if peer is None:
        await _enviar(eu, {"tipo": "procurando"})
    else:
        await _enviar(eu, {"tipo": "achou", "sala": eu.sala, "oponente": peer.nome})

    # Daqui pra frente o servidor é só um cano: o que chega de um lado sai
    # igualzinho no outro. Quem sabe o que é palpite, placar e fim de jogo é o
    # cliente — o servidor nunca abre o envelope.
    try:
        while True:
            msg = await ws.receive_text()
            if eu.oponente is not None:
                await _texto(eu.oponente, msg)
    except WebSocketDisconnect:
        pass
    finally:
        await _sair(eu)
