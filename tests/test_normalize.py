from datetime import date

from balcao.normalize import data_br, limpa_texto, normaliza_uf, para_data, so_digitos


def test_so_digitos_limpa_mascara():
    assert so_digitos("12.345.678/0001-90") == "12345678000190"
    assert so_digitos("123.456.789-00") == "12345678900"


def test_so_digitos_vazio_vira_none():
    assert so_digitos("") is None
    assert so_digitos(None) is None
    assert so_digitos("abc") is None


def test_para_data_iso():
    assert para_data("2025-01-15") == date(2025, 1, 15)
    assert para_data("2025-01-15T00:00:00") == date(2025, 1, 15)


def test_para_data_brasileira():
    assert para_data("15/01/2025") == date(2025, 1, 15)


def test_para_data_invalida_vira_none():
    assert para_data("") is None
    assert para_data(None) is None
    assert para_data("ontem") is None


def test_data_br_traduz_iso():
    assert data_br("2025-01-15") == "15/01/2025"
    assert data_br("invalida") is None


def test_limpa_texto():
    assert limpa_texto("  MANUTENÇÃO   DE  ESCRITÓRIO. ") == "MANUTENÇÃO DE ESCRITÓRIO"
    assert limpa_texto(None) == ""


def test_normaliza_uf():
    assert normaliza_uf("sp") == "SP"
    assert normaliza_uf(" RJ ") == "RJ"
    assert normaliza_uf("XX") is None
    assert normaliza_uf(None) is None
