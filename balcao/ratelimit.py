from slowapi import Limiter
from slowapi.util import get_remote_address


def cria_limiter(limite: str) -> Limiter:
    return Limiter(key_func=get_remote_address, default_limits=[limite])
