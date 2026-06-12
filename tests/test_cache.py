from balcao.cache import CacheRespostas
from balcao.connectors.base import NormalizedResponse


def resposta_qualquer() -> NormalizedResponse:
    return NormalizedResponse(fonte="camara", recurso="deputados", dados=[], total=0)


def test_chave_ignora_ordem_dos_params():
    a = CacheRespostas.chave("camara", "deputados", {"uf": "SP", "itens": "3"})
    b = CacheRespostas.chave("camara", "deputados", {"itens": "3", "uf": "SP"})
    assert a == b


def test_chave_muda_com_params_diferentes():
    a = CacheRespostas.chave("camara", "deputados", {"uf": "SP"})
    b = CacheRespostas.chave("camara", "deputados", {"uf": "RJ"})
    assert a != b


def test_guarda_e_pega():
    cache = CacheRespostas(ttl=60)
    cache.guarda("chave", resposta_qualquer())
    assert cache.pega("chave") is not None
    assert cache.pega("outra") is None


def test_ttl_expira():
    relogio = {"agora": 0.0}
    cache = CacheRespostas(ttl=10, timer=lambda: relogio["agora"])
    cache.guarda("chave", resposta_qualquer())
    assert cache.pega("chave") is not None
    relogio["agora"] = 11.0
    assert cache.pega("chave") is None
